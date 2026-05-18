"""Internal helper for geo-prompt-library-v2 scripts.

Provides:
  - Credential loading (env vars, then walk-up .env discovery)
  - Hand-rolled .env parser (no python-dotenv dependency)
  - Minimal stdlib DataForSEO API client (urllib + base64 + json)
  - Preflight check_setup() (offline; just verifies credentials are loadable)
  - SetupError and APIError exception types

Not user-facing. Imported by sibling scripts.

Python 3.9+. Pure stdlib.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_URL = "https://api.dataforseo.com/v3"
USER_AGENT = "geo-prompt-library-v2/1.0"
API_SUCCESS_CODE = 20000
API_AUTH_ERROR_CODE = 40100


class SetupError(Exception):
    """Credentials missing or unreadable."""


class APIError(Exception):
    """DataForSEO API call failed (auth, network, or non-success status)."""


# ---------------------------------------------------------------------------
# .env parsing and credential loading
# ---------------------------------------------------------------------------

def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a .env file. Stdlib-only; no interpolation, no multi-line values.

    Tolerates: blank lines, '#' comment lines (with optional leading whitespace),
    BOM, CRLF/LF line endings, surrounding single or double quotes on values.
    """
    result: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8-sig")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (len(value) >= 2) and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def _walk_up_for_env(start: Path) -> Optional[Path]:
    """Walk up from start looking for a .env file.

    Stop conditions (first wins):
      1. A directory containing a .env file: return that .env path.
      2. A directory containing .claude/ or .git/ (workspace marker): stop and
         return that directory's .env if present, else None.
      3. $HOME: stop and return $HOME/.env if present, else None.
      4. Filesystem root.
    """
    home = Path.home().resolve()
    current = start.resolve()
    if current.is_file():
        current = current.parent

    visited: Set[Path] = set()
    while True:
        visited.add(current)
        env_candidate = current / ".env"
        if env_candidate.is_file():
            return env_candidate
        if (current / ".claude").exists() or (current / ".git").exists():
            return None
        if current == home:
            return None
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Script lives outside $HOME: also check $HOME/.env as a sibling fallback.
    if home not in visited:
        home_env = home / ".env"
        if home_env.is_file():
            return home_env
    return None


def load_credentials() -> Tuple[str, str]:
    """Return (username, password). Raises SetupError on failure.

    Resolution order:
      1. DATAFORSEO_USERNAME + DATAFORSEO_PASSWORD env vars (both set, non-empty).
      2. Walk-up .env discovery from this file's location.
    """
    env_user = os.environ.get("DATAFORSEO_USERNAME", "").strip()
    env_pass = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    if env_user and env_pass:
        return env_user, env_pass

    env_path = _walk_up_for_env(Path(__file__).resolve().parent)
    if env_path is not None:
        parsed = parse_env_file(env_path)
        file_user = parsed.get("DATAFORSEO_USERNAME", "").strip()
        file_pass = parsed.get("DATAFORSEO_PASSWORD", "").strip()
        if file_user and file_pass:
            return file_user, file_pass

        missing = []
        if not file_user:
            missing.append("DATAFORSEO_USERNAME")
        if not file_pass:
            missing.append("DATAFORSEO_PASSWORD")
        raise SetupError(_setup_message(
            missing_detail=f"Found .env at {env_path} but {', '.join(missing)} missing or empty."
        ))

    detail_parts = []
    if not env_user:
        detail_parts.append("DATAFORSEO_USERNAME env var not set")
    if not env_pass:
        detail_parts.append("DATAFORSEO_PASSWORD env var not set")
    detail_parts.append("no .env file found via walk-up from script location")
    raise SetupError(_setup_message(missing_detail="; ".join(detail_parts) + "."))


def _setup_message(missing_detail: str) -> str:
    return f"""ERROR: DataForSEO credentials not found.

Missing: {missing_detail}

Set credentials one of two ways:

1. Environment variables (preferred for CI/automation):
     export DATAFORSEO_USERNAME="your_username"
     export DATAFORSEO_PASSWORD="your_password"

2. .env file in your workspace root (or any ancestor of this skill):
     DATAFORSEO_USERNAME=your_username
     DATAFORSEO_PASSWORD=your_password

Get credentials at https://dataforseo.com (sign up, then copy from your dashboard).

Verify with:
     python3 {_skill_root()}/scripts/check_setup.py

Full setup guide: {_skill_root()}/references/setup.md
"""


def _skill_root() -> str:
    return str(Path(__file__).resolve().parent.parent)


def check_setup() -> None:
    """Offline preflight: validates credentials can be loaded.

    Does NOT validate credential correctness (only a real API call confirms),
    DOES NOT ping the network. Use check_setup.py for end-to-end verification.
    """
    load_credentials()


# ---------------------------------------------------------------------------
# DataForSEO HTTP client
# ---------------------------------------------------------------------------

def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
    return f"Basic {token}"


def dataforseo_request(
    endpoint_path: str,
    payload: Any,
    *,
    timeout: int = 30,
) -> Dict[str, Any]:
    """POST to BASE_URL/endpoint_path with HTTP Basic Auth. Returns parsed JSON.

    Single 429 retry with 60s sleep. Raises APIError on non-success.
    Auth failures arrive as HTTP 200 with JSON status_code=40100, not HTTP 401.
    """
    username, password = load_credentials()
    url = f"{BASE_URL}/{endpoint_path.lstrip('/')}"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": _auth_header(username, password),
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    context = ssl.create_default_context()

    def _do_request() -> Tuple[int, Dict[str, Any]]:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                http_status = resp.status
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            http_status = e.code
            raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            if http_status == 429:
                return http_status, {}
            if not raw:
                raise APIError(f"HTTP {http_status} from DataForSEO with no response body") from e
        except urllib.error.URLError as e:
            raise APIError(f"Network error contacting DataForSEO: {e.reason}") from e
        except socket.timeout as e:
            raise APIError(f"Timed out after {timeout}s waiting for DataForSEO") from e

        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            raise APIError(f"DataForSEO returned non-JSON (HTTP {http_status}): {raw[:200]}") from e
        return http_status, parsed

    http_status, data = _do_request()
    if http_status == 429:
        time.sleep(60)
        http_status, data = _do_request()
        if http_status == 429:
            raise APIError("DataForSEO rate limit (429) persisted after one retry with 60s backoff")

    status_code = data.get("status_code") if isinstance(data, dict) else None
    if status_code == API_SUCCESS_CODE:
        return data
    if status_code == API_AUTH_ERROR_CODE:
        raise APIError(
            "Authentication failed (DataForSEO status_code 40100). "
            "Check DATAFORSEO_USERNAME and DATAFORSEO_PASSWORD."
        )
    status_message = data.get("status_message", "unknown error") if isinstance(data, dict) else "no JSON body"
    raise APIError(f"DataForSEO returned status_code={status_code}: {status_message}")


# ---------------------------------------------------------------------------
# Endpoint wrappers
# ---------------------------------------------------------------------------

def ranked_keywords(
    url: str,
    *,
    limit: int = 20,
    min_volume: int = 10,
    max_position: int = 10,
    location: str = "United States",
    language: str = "English",
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """Keywords the URL ranks for in Google (organic only, filtered + sorted).

    Returns list of {keyword, search_volume, position}. Ordered by ETV desc,
    then rank ascending.
    """
    filters: List[Any] = [
        ["keyword_data.keyword_info.search_volume", ">", min_volume],
        "and",
        ["ranked_serp_element.serp_item.type", "=", "organic"],
        "and",
        ["ranked_serp_element.serp_item.rank_absolute", "<=", max_position],
    ]
    order_by = [
        "ranked_serp_element.serp_item.etv,desc",
        "ranked_serp_element.serp_item.rank_absolute,asc",
    ]
    params = {
        "target": url,
        "location_name": location,
        "language_name": language,
        "filters": filters,
        "order_by": order_by,
        "limit": limit,
    }
    # NOTE: ranked_keywords uses {"data": params}, NOT a list-wrapped payload.
    response = dataforseo_request(
        "dataforseo_labs/google/ranked_keywords/live",
        {"data": params},
        timeout=timeout,
    )

    results: List[Dict[str, Any]] = []
    for task in response.get("tasks", []) or []:
        if not task:
            continue
        for result in task.get("result", []) or []:
            if not result:
                continue
            for item in result.get("items", []) or []:
                keyword_data = item.get("keyword_data", {}) or {}
                ranked_serp = item.get("ranked_serp_element", {}) or {}
                serp_item = ranked_serp.get("serp_item", {}) or {}
                kw = keyword_data.get("keyword")
                if not kw:
                    continue
                results.append({
                    "keyword": kw,
                    "search_volume": (keyword_data.get("keyword_info") or {}).get("search_volume") or 0,
                    "position": serp_item.get("rank_absolute") or 0,
                })
    return results


def keyword_suggestions(
    keyword: str,
    *,
    limit: int = 20,
    location: str = "United States",
    language: str = "English",
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """Keyword autocomplete suggestions for a seed term.

    Returns list of {keyword, search_volume, keyword_difficulty, competition,
    cpc, intent}. None values where data is unavailable.
    """
    params = {
        "keyword": keyword,
        "location_name": location,
        "language_name": language,
        "include_seed_keyword": False,
        "limit": limit,
    }
    # NOTE: keyword_suggestions uses [params] (list wrap), NOT {"data": params}.
    response = dataforseo_request(
        "dataforseo_labs/google/keyword_suggestions/live",
        [params],
        timeout=timeout,
    )

    results: List[Dict[str, Any]] = []
    for task in response.get("tasks", []) or []:
        if not task:
            continue
        for result in task.get("result", []) or []:
            if not result:
                continue
            for item in result.get("items", []) or []:
                kw = item.get("keyword")
                if not kw:
                    continue
                kw_info = item.get("keyword_info") or {}
                kw_props = item.get("keyword_properties") or {}
                intent_info = item.get("search_intent_info") or {}
                results.append({
                    "keyword": kw,
                    "search_volume": kw_info.get("search_volume") or 0,
                    "keyword_difficulty": kw_props.get("keyword_difficulty"),
                    "competition": kw_info.get("competition"),
                    "cpc": kw_info.get("cpc"),
                    "intent": intent_info.get("main_intent"),
                })
    return results


# ---------------------------------------------------------------------------
# CLI entrypoint helper
# ---------------------------------------------------------------------------

def run_with_setup_check(fn) -> None:
    """Wrap a script main() in setup + standard error handling.

    Exit codes:
      0 success | 1 generic | 2 invalid args | 3 input not found
      4 API/network | 5 setup incomplete
    """
    try:
        fn()
    except SetupError as e:
        print(str(e), file=sys.stderr)
        sys.exit(5)
    except APIError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(4)
    except FileNotFoundError as e:
        print(f"Input not found: {e}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
