#!/usr/bin/env python3
"""Verify DataForSEO credentials work end-to-end.

Runs the offline credential loader, then makes one real API call
(`keyword_suggestions("test", limit=1)`) to confirm credentials are valid.

Consumes ~1 DataForSEO API row per run (~$0.0001 at typical pricing).

Exit codes:
  0  All checks passed; credentials are valid.
  4  API or network error (bad creds, network down, etc.).
  5  Setup incomplete (no credentials found).

Examples:
  python3 check_setup.py
  python3 check_setup.py --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    APIError,
    SetupError,
    _walk_up_for_env,
    keyword_suggestions,
    load_credentials,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print resolved credential source (env vars or .env path)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        username, _password = load_credentials()
    except SetupError as e:
        print(str(e), file=sys.stderr)
        sys.exit(5)

    if args.verbose:
        env_user = os.environ.get("DATAFORSEO_USERNAME", "").strip()
        env_pass = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
        if env_user and env_pass:
            source = "environment variables (DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD)"
        else:
            env_path = _walk_up_for_env(Path(__file__).resolve().parent)
            source = f".env file at {env_path}"
        print(f"Credential source: {source}", file=sys.stderr)
        print(f"Username: {username}", file=sys.stderr)

    print("Pinging DataForSEO with a test keyword_suggestions call...", file=sys.stderr)
    try:
        results = keyword_suggestions("test", limit=1)
    except APIError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(4)

    print(f"OK: DataForSEO credentials valid (returned {len(results)} result(s) for \"test\").")
    sys.exit(0)


if __name__ == "__main__":
    main()
