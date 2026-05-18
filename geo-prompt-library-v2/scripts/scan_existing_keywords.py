#!/usr/bin/env python3
"""Consolidate keyword CSVs the user has uploaded or pointed at.

Accepts one or more file or directory paths via --paths. For each path:
  - File: read directly as a CSV.
  - Directory: recursively walk for *.csv files.

Looks for CSVs that have a `keyword` column AND a `search_volume`-style column
(flexible header matching — see KEYWORD_COL_RE / VOLUME_COL_RE below). Rows
are deduplicated by lowercase keyword (keeping the highest volume) and sorted
by volume descending. Output is RFC-4180 CSV with QUOTE_MINIMAL.

No DataForSEO API calls. No preflight needed.

Exit codes:
  0  Success (even if no qualifying rows found — emits empty CSV with a warning)
  2  Invalid arguments
  3  One of the supplied paths does not exist

Examples:
  python3 scan_existing_keywords.py --paths brand-research.csv
  python3 scan_existing_keywords.py --paths uploads/ --out geo_tracking/output/existing-keywords.csv
  python3 scan_existing_keywords.py --paths a.csv b.csv uploads/ --min-volume 50
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_SEP = r"[\s_-]*"  # separator class: whitespace, underscore, hyphen, or none
KEYWORD_COL_RE = re.compile(rf"^(keyword|query|term|search{_SEP}term)$", re.IGNORECASE)
VOLUME_COL_RE = re.compile(
    rf"^("
    rf"search{_SEP}volume"
    rf"|volume"
    rf"|monthly{_SEP}searches?"
    rf"|avg{_SEP}monthly{_SEP}searches?"
    rf"|sv"
    rf"|total{_SEP}sv(\s*\(.*\))?"
    rf"|search{_SEP}vol"
    rf")$",
    re.IGNORECASE,
)


def _normalize_col(name: str) -> str:
    """Collapse whitespace (including embedded newlines) and strip."""
    return re.sub(r"\s+", " ", name).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="One or more file or directory paths to scan. Files are read directly; directories are walked recursively for *.csv.",
    )
    parser.add_argument("--out", help="Output CSV path (default: stdout)")
    parser.add_argument(
        "--min-volume",
        type=int,
        default=0,
        help="Drop rows with search_volume below this threshold (default: 0)",
    )
    return parser.parse_args()


def find_columns(fieldnames: List[str]) -> Optional[Tuple[str, str]]:
    """Return (keyword_col, volume_col) or None if file doesn't qualify."""
    keyword_col = None
    volume_col = None
    for name in fieldnames:
        if name is None:
            continue
        normalized = _normalize_col(name)
        if not normalized:
            continue
        if keyword_col is None and KEYWORD_COL_RE.match(normalized):
            keyword_col = name
        if volume_col is None and VOLUME_COL_RE.match(normalized):
            volume_col = name
    if keyword_col and volume_col:
        return keyword_col, volume_col
    return None


def parse_volume(raw: str) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if not s or s.lower() in ("none", "n/a", "na", "-"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def scan_csv(csv_path: Path) -> List[Dict[str, str]]:
    """Read one CSV; return qualifying rows or []."""
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            cols = find_columns(list(reader.fieldnames))
            if cols is None:
                return []
            keyword_col, volume_col = cols
            rows: List[Dict[str, str]] = []
            for row in reader:
                kw = (row.get(keyword_col) or "").strip()
                if not kw:
                    continue
                vol = parse_volume(row.get(volume_col, ""))
                if vol is None:
                    continue
                rows.append({"keyword": kw, "search_volume": str(vol)})
            return rows
    except (UnicodeDecodeError, csv.Error, OSError) as e:
        print(f"  skip {csv_path}: {e}", file=sys.stderr)
        return []


def gather_csvs(paths: List[str]) -> List[Path]:
    """Resolve each --paths entry to a flat list of *.csv files."""
    out: List[Path] = []
    for raw in paths:
        p = Path(raw).resolve()
        if not p.exists():
            print(f"ERROR: path not found: {raw}", file=sys.stderr)
            sys.exit(3)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.csv")))
    return out


def write_output(out_path: Optional[str], rows: List[Dict[str, str]]) -> None:
    headers = ["keyword", "search_volume", "source_file"]
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=headers, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    csv_paths = gather_csvs(args.paths)

    aggregate: Dict[str, Tuple[int, Path]] = {}
    qualifying_files = 0

    for csv_path in csv_paths:
        rows = scan_csv(csv_path)
        if not rows:
            continue
        qualifying_files += 1
        print(f"  scanned: {csv_path}", file=sys.stderr)
        for row in rows:
            key = row["keyword"].lower().strip()
            vol = int(row["search_volume"])
            if vol < args.min_volume:
                continue
            existing = aggregate.get(key)
            if existing is None or vol > existing[0]:
                aggregate[key] = (vol, csv_path)

    output_rows = [
        {
            "keyword": kw,
            "search_volume": str(vol),
            "source_file": str(src),
        }
        for kw, (vol, src) in sorted(aggregate.items(), key=lambda kv: -kv[1][0])
    ]

    print(
        f"Found {len(output_rows)} unique keywords across {qualifying_files} source file(s).",
        file=sys.stderr,
    )
    if qualifying_files == 0:
        print(
            "INFO: no CSVs contained both a keyword column and a search_volume column. "
            "Skip --existing on the validate_prompt_keywords.py call.",
            file=sys.stderr,
        )

    write_output(args.out, output_rows)
    sys.exit(0)


if __name__ == "__main__":
    main()
