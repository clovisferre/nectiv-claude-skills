#!/usr/bin/env python3
"""Batched keyword-suggestions expansion across N seed terms.

For each seed keyword, calls DataForSEO keyword_suggestions and aggregates
all returned keywords into a single deduped CSV with a `seeds` column
recording which input seeds produced each result. On conflict (same keyword
from multiple seeds), keeps the highest search_volume.

Exit codes:
  0  Success
  2  Invalid arguments
  3  Seeds file not found
  4  DataForSEO API/network error
  5  Setup incomplete

Examples:
  python3 expand_topic_keywords.py --seeds "wholesale" "marketplace" --out exp.csv
  python3 expand_topic_keywords.py --seeds-file seeds.txt --limit-per-seed 50
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import keyword_suggestions, run_with_setup_check  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--seeds", nargs="+", help="Seed keywords (space-separated)")
    parser.add_argument("--seeds-file", help="Path to text file with one seed per line")
    parser.add_argument("--out", help="Output CSV path (default: stdout)")
    parser.add_argument(
        "--limit-per-seed", type=int, default=30, help="Max results per seed (default: 30)"
    )
    parser.add_argument("--timeout", type=int, default=30, help="API timeout per call (default: 30)")
    return parser.parse_args()


def load_seeds(args: argparse.Namespace) -> List[str]:
    seeds: List[str] = []
    if args.seeds:
        seeds.extend(s.strip() for s in args.seeds if s.strip())
    if args.seeds_file:
        seeds_path = Path(args.seeds_file)
        if not seeds_path.is_file():
            raise FileNotFoundError(f"Seeds file not found: {args.seeds_file}")
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                seeds.append(line)
    # Dedupe while preserving order
    seen = set()
    unique: List[str] = []
    for s in seeds:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)
    return unique


def write_csv(out_path: Optional[str], rows: List[Dict[str, Any]]) -> None:
    headers = ["keyword", "search_volume", "keyword_difficulty", "intent", "seeds"]

    def _emit(stream: Any) -> None:
        writer = csv.DictWriter(stream, fieldnames=headers, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in headers})

    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            _emit(f)
    else:
        _emit(sys.stdout)


def _main() -> None:
    args = parse_args()
    if not args.seeds and not args.seeds_file:
        print("ERROR: must pass --seeds or --seeds-file", file=sys.stderr)
        sys.exit(2)

    seeds = load_seeds(args)
    if not seeds:
        print("ERROR: no seeds resolved (empty list)", file=sys.stderr)
        sys.exit(2)

    aggregate: Dict[str, Dict[str, Any]] = {}
    for i, seed in enumerate(seeds, 1):
        print(f"  [{i}/{len(seeds)}] keyword_suggestions for '{seed}'...", file=sys.stderr)
        results = keyword_suggestions(seed, limit=args.limit_per_seed, timeout=args.timeout)
        for r in results:
            kw = r["keyword"]
            key = kw.lower().strip()
            vol = r.get("search_volume") or 0
            existing = aggregate.get(key)
            if existing is None:
                aggregate[key] = {
                    "keyword": kw,
                    "search_volume": vol,
                    "keyword_difficulty": r.get("keyword_difficulty"),
                    "intent": r.get("intent"),
                    "seeds_list": [seed],
                }
            else:
                if vol > (existing.get("search_volume") or 0):
                    existing["search_volume"] = vol
                    existing["keyword_difficulty"] = r.get("keyword_difficulty")
                    existing["intent"] = r.get("intent")
                if seed not in existing["seeds_list"]:
                    existing["seeds_list"].append(seed)

    rows = sorted(aggregate.values(), key=lambda r: -(r.get("search_volume") or 0))
    for r in rows:
        r["seeds"] = ";".join(r.pop("seeds_list"))

    print(f"Aggregated {len(rows)} unique keywords from {len(seeds)} seed(s).", file=sys.stderr)
    write_csv(args.out, rows)


def main() -> None:
    run_with_setup_check(_main)


if __name__ == "__main__":
    main()
