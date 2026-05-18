#!/usr/bin/env python3
"""Phase 4: validate that every prompt's supporting_keyword has real search demand.

Reads a prompts CSV with at least `text` and `supporting_keyword` columns.
For each row, looks up the search volume of `supporting_keyword` and writes
the result back to a `search_volume` column with a `status` column.

NEVER overwrites `supporting_keyword`. When a keyword can't be confirmed
(not_found / zero_volume), populates a `candidate_keywords` column with up to
5 alternatives from the API for the agent to consider on the next pass.

Pass order:
  1. If --existing is provided, check it first (case-insensitive exact match).
     Hit -> status=from_existing, search_volume from existing CSV, skip API.
  2. Otherwise call keyword_suggestions(supporting_keyword, limit=5):
       - Exact lowercased match in results -> status=ok
       - Found but search_volume == 0 -> status=zero_volume
       - No exact match -> status=not_found

Caching: By default rows already marked status=ok or status=from_existing with
search_volume > 0 are SKIPPED on re-runs. This saves ~95% of API calls on
iteration. IMPORTANT: if you change a row's supporting_keyword, also clear that
row's status (and search_volume) so it gets re-validated. Pass --force to
re-validate every row regardless of prior status.

Runtime: ~1 second per API call at typical network latency. A 100-row library
validates in ~2 minutes on first run; revision iterations are much faster
because already-validated rows are skipped.

`candidate_keywords` format: `"kw1 (vol1); kw2 (vol2); ..."`. Brittle if a
candidate contains `;` or `()` — rare for SEO keywords but documented.

Exit codes:
  0  Run completed (some rows may be not_found/zero_volume — that's expected)
  2  Invalid arguments
  3  Prompts CSV not found
  4  DataForSEO API/network error preventing completion
  5  Setup incomplete

Examples:
  python3 validate_prompt_keywords.py --prompts prompts.csv --out prompts.csv
  python3 validate_prompt_keywords.py --prompts prompts.csv --existing existing-keywords.csv --out prompts.csv
  python3 validate_prompt_keywords.py --prompts prompts.csv --out prompts.csv --force
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import APIError, keyword_suggestions, run_with_setup_check  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--prompts", required=True, help="Input prompts CSV path")
    parser.add_argument("--out", required=True, help="Output CSV path (may equal --prompts)")
    parser.add_argument("--existing", help="CSV of pre-vetted keywords (output of scan_existing_keywords.py)")
    parser.add_argument("--timeout", type=int, default=30, help="Per-API-call timeout in seconds (default: 30)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-validate every row, even rows already marked status=ok or from_existing. "
             "Default: skip already-validated rows with search_volume > 0 (saves API calls on iteration).",
    )
    return parser.parse_args()


def load_existing(path: Optional[str]) -> Dict[str, int]:
    """Returns lowercase keyword -> search_volume."""
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"--existing CSV not found: {path}")
    out: Dict[str, int] = {}
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = (row.get("keyword") or "").strip().lower()
            if not kw:
                continue
            try:
                vol = int(float(str(row.get("search_volume", "0")).replace(",", "")))
            except (ValueError, TypeError):
                continue
            if kw not in out or vol > out[kw]:
                out[kw] = vol
    return out


def format_candidates(results: List[Dict[str, Any]], limit: int = 5) -> str:
    parts = []
    for r in results[:limit]:
        kw = r.get("keyword", "")
        vol = r.get("search_volume") or 0
        parts.append(f"{kw} ({vol})")
    return "; ".join(parts)


def write_atomic(out_path: str, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    """Atomic write via tempfile in the same directory, then os.replace."""
    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".validate_tmp_", suffix=".csv", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            writer.writeheader()
            for r in rows:
                writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _main() -> None:
    args = parse_args()

    prompts_path = Path(args.prompts)
    if not prompts_path.is_file():
        raise FileNotFoundError(f"Prompts CSV not found: {args.prompts}")

    existing = load_existing(args.existing)
    if existing:
        print(f"Loaded {len(existing)} pre-vetted keywords from {args.existing}", file=sys.stderr)

    with prompts_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        original_fieldnames = list(reader.fieldnames or [])
        if "supporting_keyword" not in original_fieldnames:
            print("ERROR: prompts CSV must have a 'supporting_keyword' column", file=sys.stderr)
            sys.exit(2)
        rows = list(reader)

    fieldnames = list(original_fieldnames)
    for col in ("search_volume", "status", "candidate_keywords"):
        if col not in fieldnames:
            fieldnames.append(col)

    counts: Dict[str, int] = {
        "blank": 0, "from_existing": 0, "ok": 0,
        "not_found": 0, "zero_volume": 0, "error": 0,
        "skipped_cached": 0,
    }

    for i, row in enumerate(rows, 1):
        kw_raw = (row.get("supporting_keyword") or "").strip()
        # Cache: skip rows already marked ok/from_existing with vol > 0
        # unless --force or supporting_keyword is now blank.
        if not args.force and kw_raw:
            prior_status = (row.get("status") or "").strip().lower()
            prior_vol_raw = (row.get("search_volume") or "").strip().replace(",", "")
            try:
                prior_vol = int(float(prior_vol_raw)) if prior_vol_raw else 0
            except (ValueError, TypeError):
                prior_vol = 0
            if prior_status in ("ok", "from_existing") and prior_vol > 0:
                counts["skipped_cached"] += 1
                if i % 10 == 0:
                    print(f"  processed {i}/{len(rows)}...", file=sys.stderr)
                continue

        if not kw_raw:
            row["status"] = "blank"
            row["search_volume"] = ""
            row["candidate_keywords"] = ""
            counts["blank"] += 1
        else:
            kw_lower = kw_raw.lower()
            # Pass 1: existing CSV
            if kw_lower in existing:
                row["search_volume"] = str(existing[kw_lower])
                row["status"] = "from_existing"
                row["candidate_keywords"] = ""
                counts["from_existing"] += 1
            else:
                # Pass 2: API call. Narrow to APIError so SetupError still propagates
                # to run_with_setup_check (which exits 5).
                try:
                    results = keyword_suggestions(kw_raw, limit=5, timeout=args.timeout)
                except APIError as e:
                    row["status"] = "error"
                    row["search_volume"] = ""
                    row["candidate_keywords"] = ""
                    counts["error"] += 1
                    print(f"  row {i}: error querying '{kw_raw}': {e}", file=sys.stderr)
                else:
                    exact = next(
                        (r for r in results if (r.get("keyword") or "").lower() == kw_lower),
                        None,
                    )
                    if exact is not None:
                        vol = exact.get("search_volume") or 0
                        if vol > 0:
                            row["search_volume"] = str(vol)
                            row["status"] = "ok"
                            row["candidate_keywords"] = ""
                            counts["ok"] += 1
                        else:
                            row["search_volume"] = "0"
                            row["status"] = "zero_volume"
                            row["candidate_keywords"] = format_candidates(results)
                            counts["zero_volume"] += 1
                    else:
                        row["search_volume"] = ""
                        row["status"] = "not_found"
                        row["candidate_keywords"] = format_candidates(results)
                        counts["not_found"] += 1

        if i % 10 == 0:
            print(f"  processed {i}/{len(rows)}...", file=sys.stderr)

    print(f"\nDone. {len(rows)} rows processed.", file=sys.stderr)
    summary = " ".join(f"{k}={v}" for k, v in counts.items())
    print(f"Summary: {summary}", file=sys.stderr)

    write_atomic(args.out, fieldnames, rows)


def main() -> None:
    run_with_setup_check(_main)


if __name__ == "__main__":
    main()
