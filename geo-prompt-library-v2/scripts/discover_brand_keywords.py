#!/usr/bin/env python3
"""Phase 1c: discover what keywords a brand's domain ranks for in Google.

Wraps the DataForSEO ranked_keywords endpoint, filtered to organic results in
the top N positions, and emits a clean CSV.

Exit codes:
  0  Success
  2  Invalid arguments
  4  DataForSEO API/network error
  5  Setup incomplete

Examples:
  python3 discover_brand_keywords.py --url salesforce.com --out brand-ranked.csv
  python3 discover_brand_keywords.py --url https://hubspot.com --limit 100 --min-volume 50
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ranked_keywords, run_with_setup_check  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="Brand domain or full URL")
    parser.add_argument("--out", help="Output CSV path (default: stdout)")
    parser.add_argument("--limit", type=int, default=50, help="Max keywords (default: 50)")
    parser.add_argument("--min-volume", type=int, default=10, help="Min search volume (default: 10)")
    parser.add_argument("--max-position", type=int, default=10, help="Max SERP position (default: 10)")
    parser.add_argument("--timeout", type=int, default=30, help="API timeout in seconds (default: 30)")
    return parser.parse_args()


def write_csv(out_path: str, rows: List[dict]) -> None:
    headers = ["keyword", "search_volume", "position"]
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in headers})
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=headers, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})


def _main() -> None:
    args = parse_args()
    print(f"Querying ranked keywords for {args.url}...", file=sys.stderr)
    results = ranked_keywords(
        args.url,
        limit=args.limit,
        min_volume=args.min_volume,
        max_position=args.max_position,
        timeout=args.timeout,
    )
    print(f"Got {len(results)} keyword(s).", file=sys.stderr)
    if not results:
        print(
            "HINT: 0 keywords returned. The brand may not rank in the top "
            f"{args.max_position} for any keyword with volume >= {args.min_volume}. "
            "Try loosening filters, e.g.: --max-position 30 --min-volume 1",
            file=sys.stderr,
        )
    write_csv(args.out, results)


def main() -> None:
    run_with_setup_check(_main)


if __name__ == "__main__":
    main()
