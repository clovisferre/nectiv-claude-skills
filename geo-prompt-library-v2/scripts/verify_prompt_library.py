#!/usr/bin/env python3
"""Phase 5: deterministic verification of a completed prompt-tracking library.

Runs hard-fail checks (CSV parses, columns complete, every row has volume > 0,
brand=TRUE matches the brand name appearing in text) and emits a markdown
report with soft-warning distribution analysis (segments, intent, branded vs
generic, top keywords).

No DataForSEO API calls. No preflight needed.

Exit codes:
  0  All hard checks passed
  1  At least one hard check failed
  2  Invalid arguments
  3  Input CSV not found

Examples:
  python3 verify_prompt_library.py --csv prompts.csv --brand Salesforce
  python3 verify_prompt_library.py --csv prompts.csv --brand Salesforce --target-count 130 --claude-md /path/to/CLAUDE.md
  python3 verify_prompt_library.py --csv prompts.csv --brand Salesforce --output-format json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_COLUMNS = ["text", "segments", "intent", "brand", "supporting_keyword", "search_volume"]
DEFAULT_INTENTS = ["Informational", "Transactional", "Comparison", "Navigational"]
GUIDANCE_MARKER = "> [GUIDANCE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--csv", required=True, help="Prompt-tracking-library CSV path")
    parser.add_argument("--brand", required=True, help="Brand name for brand=TRUE consistency check")
    parser.add_argument(
        "--brand-aliases",
        default="",
        help="Comma-separated proprietary terms that legitimately mark a prompt as branded "
             "without containing the brand name itself (e.g., feature names, product line names). "
             "Example: --brand-aliases \"Florium,GelShift\". The brand consistency check passes if "
             "the text contains the brand name OR any alias (case-insensitive substring).",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        help="Expected total prompts (flags off-target if >15%% deviation)",
    )
    parser.add_argument(
        "--target-intent",
        default="25/30/35/10",
        help="Target intent distribution as %% pct for I/T/C/N (default: 25/30/35/10 — "
             "GEO-weighted toward decision-stage prompts; pass --target-intent 60/15/15/10 "
             "for conventional SEO).",
    )
    parser.add_argument(
        "--output-format",
        choices=["markdown", "json"],
        default="markdown",
        help="Report format (default: markdown)",
    )
    parser.add_argument(
        "--claude-md",
        help="Optional: also scan a rendered geo_tracking/CLAUDE.md for residual > [GUIDANCE blocks",
    )
    return parser.parse_args()


def parse_intent_targets(spec: str) -> Dict[str, float]:
    parts = [p.strip() for p in spec.split("/")]
    if len(parts) != 4:
        raise ValueError(f"--target-intent expects 4 slash-separated numbers, got: {spec}")
    nums = [float(p) for p in parts]
    return dict(zip(DEFAULT_INTENTS, nums))


def parse_volume(raw: str) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def run_checks(
    csv_path: Path,
    brand: str,
    target_count: Optional[int],
    intent_targets: Dict[str, float],
    claude_md: Optional[Path],
    brand_aliases: Optional[List[str]] = None,
) -> Dict[str, Any]:
    brand_aliases = brand_aliases or []
    report: Dict[str, Any] = {
        "csv_path": str(csv_path),
        "brand": brand,
        "hard_checks": [],
        "soft_warnings": [],
        "distributions": {},
        "all_hard_passed": True,
    }

    if not csv_path.is_file():
        report["hard_checks"].append({"name": "csv_exists", "passed": False, "detail": f"file not found: {csv_path}"})
        report["all_hard_passed"] = False
        return report

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError) as e:
        report["hard_checks"].append({"name": "csv_parses", "passed": False, "detail": str(e)})
        report["all_hard_passed"] = False
        return report

    report["hard_checks"].append({"name": "csv_parses", "passed": True, "detail": f"{len(rows)} rows"})

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing_cols:
        report["hard_checks"].append({
            "name": "required_columns_present",
            "passed": False,
            "detail": f"missing: {missing_cols}",
        })
        report["all_hard_passed"] = False
        return report
    report["hard_checks"].append({"name": "required_columns_present", "passed": True, "detail": ""})

    rows_with_blank: List[int] = []
    rows_zero_or_missing_volume: List[int] = []
    rows_brand_mismatch: List[Dict[str, Any]] = []

    brand_match_terms = [brand.lower()] + [a.lower() for a in brand_aliases if a]
    intent_counter: Counter = Counter()
    segment_counter: Counter = Counter()
    brand_true_count = 0
    keywords_by_vol: List[tuple] = []
    year_re = re.compile(r"\b(19|20)\d{2}\b")
    year_offenders: List[Dict[str, Any]] = []
    best_opener_count = 0

    for i, row in enumerate(rows, 1):
        for col in REQUIRED_COLUMNS:
            if not (row.get(col) or "").strip():
                rows_with_blank.append(i)
                break

        vol = parse_volume(row.get("search_volume", ""))
        if vol is None or vol <= 0:
            rows_zero_or_missing_volume.append(i)

        text = row.get("text") or ""
        text_lower = text.lower()
        brand_raw = (row.get("brand") or "").strip().upper()
        is_brand_true = brand_raw in ("TRUE", "1", "YES", "T")
        text_has_brand = any(term in text_lower for term in brand_match_terms)
        if is_brand_true != text_has_brand:
            rows_brand_mismatch.append({
                "row": i,
                "brand_field": row.get("brand"),
                "text_has_brand": text_has_brand,
            })
        if is_brand_true:
            brand_true_count += 1

        # Soft signals collected during the row pass
        if text_lower.lstrip().startswith("best "):
            best_opener_count += 1
        if year_re.search(text):
            year_offenders.append({"row": i, "text": text})

        intent_counter[(row.get("intent") or "").strip()] += 1
        segs = (row.get("segments") or "").strip()
        if segs:
            # Split only on `;` — commas can legitimately appear within segment names.
            for seg in segs.split(";"):
                seg = seg.strip()
                if seg:
                    segment_counter[seg] += 1

        kw = (row.get("supporting_keyword") or "").strip()
        if kw and vol:
            keywords_by_vol.append((kw, vol))

    if rows_with_blank:
        report["hard_checks"].append({
            "name": "all_columns_populated",
            "passed": False,
            "detail": f"{len(rows_with_blank)} row(s) with blank required cells: {rows_with_blank[:10]}{'...' if len(rows_with_blank) > 10 else ''}",
        })
        report["all_hard_passed"] = False
    else:
        report["hard_checks"].append({"name": "all_columns_populated", "passed": True, "detail": ""})

    if rows_zero_or_missing_volume:
        report["hard_checks"].append({
            "name": "search_volume_above_zero",
            "passed": False,
            "detail": f"{len(rows_zero_or_missing_volume)} row(s) with missing/zero volume: {rows_zero_or_missing_volume[:10]}{'...' if len(rows_zero_or_missing_volume) > 10 else ''}",
        })
        report["all_hard_passed"] = False
    else:
        report["hard_checks"].append({"name": "search_volume_above_zero", "passed": True, "detail": ""})

    if rows_brand_mismatch:
        report["hard_checks"].append({
            "name": "brand_field_matches_text",
            "passed": False,
            "detail": f"{len(rows_brand_mismatch)} row(s): {rows_brand_mismatch[:5]}{'...' if len(rows_brand_mismatch) > 5 else ''}",
        })
        report["all_hard_passed"] = False
    else:
        report["hard_checks"].append({"name": "brand_field_matches_text", "passed": True, "detail": ""})

    # Soft: duplicate text
    text_counts = Counter((row.get("text") or "").strip() for row in rows)
    dupes = [t for t, n in text_counts.items() if n > 1 and t]
    if dupes:
        report["soft_warnings"].append({
            "name": "duplicate_text",
            "detail": f"{len(dupes)} duplicate prompt(s): {dupes[:5]}",
        })

    # Soft: "Best" opener overuse (GEO playbook caps at ~40%; warn above 50%)
    total = len(rows) or 1
    best_pct = best_opener_count / total * 100
    if best_pct > 50:
        report["soft_warnings"].append({
            "name": "best_opener_overuse",
            "detail": (
                f"{best_opener_count}/{total} ({best_pct:.1f}%) of prompts start with 'Best'. "
                f"Playbook target is ~40% max. Mix in noun-phrase queries (\"X options for Y\"), "
                f"personal-context openers (\"I have X, what should I use?\"), and varied question "
                f"openers (\"What works for...\", \"Any good...\", \"Which X is...\")."
            ),
        })

    # Soft: years in prompt text (playbook rule — GEO libraries must be durable)
    if year_offenders:
        sample = ", ".join(f"row {o['row']}: {o['text']!r}" for o in year_offenders[:3])
        report["soft_warnings"].append({
            "name": "year_in_prompt",
            "detail": (
                f"{len(year_offenders)} prompt(s) contain a 4-digit year. GEO prompts should be "
                f"year-free for durability (the tracking library is meant to last). Sample: {sample}"
            ),
        })

    # Distributions
    intent_dist = {k: (v, round(v / total * 100, 1)) for k, v in sorted(intent_counter.items(), key=lambda kv: -kv[1])}
    segment_dist = {k: (v, round(v / total * 100, 1)) for k, v in sorted(segment_counter.items(), key=lambda kv: -kv[1])}
    branded_pct = round(brand_true_count / total * 100, 1)

    intent_drift = []
    for intent_name, target_pct in intent_targets.items():
        actual_pct = intent_dist.get(intent_name, (0, 0.0))[1]
        if abs(actual_pct - target_pct) > 10:
            intent_drift.append(f"{intent_name}: {actual_pct}% vs target {target_pct}%")
    if intent_drift:
        report["soft_warnings"].append({"name": "intent_drift", "detail": "; ".join(intent_drift)})

    # Target count
    if target_count is not None and total > 0:
        deviation_pct = abs(total - target_count) / target_count * 100
        if deviation_pct > 15:
            report["soft_warnings"].append({
                "name": "target_count_drift",
                "detail": f"{total} prompts vs target {target_count} ({deviation_pct:.1f}% off)",
            })

    # Top 10 keywords by volume
    top_keywords = sorted(keywords_by_vol, key=lambda x: -x[1])[:10]

    report["distributions"] = {
        "total_prompts": total,
        "intent": intent_dist,
        "segments": segment_dist,
        "branded_true": brand_true_count,
        "branded_pct": branded_pct,
        "generic_pct": round(100 - branded_pct, 1),
        "top_keywords": top_keywords,
    }

    # Optional CLAUDE.md guidance scan
    if claude_md is not None:
        if not claude_md.is_file():
            report["hard_checks"].append({
                "name": "claude_md_exists",
                "passed": False,
                "detail": f"--claude-md path not found: {claude_md}",
            })
            report["all_hard_passed"] = False
        else:
            content = claude_md.read_text(encoding="utf-8")
            if GUIDANCE_MARKER in content:
                # Find line numbers for context
                offending_lines = [
                    str(i) for i, line in enumerate(content.splitlines(), 1)
                    if GUIDANCE_MARKER in line
                ]
                report["hard_checks"].append({
                    "name": "claude_md_no_guidance_leftovers",
                    "passed": False,
                    "detail": f"found '{GUIDANCE_MARKER}' on lines: {', '.join(offending_lines[:10])}",
                })
                report["all_hard_passed"] = False
            else:
                report["hard_checks"].append({
                    "name": "claude_md_no_guidance_leftovers",
                    "passed": True,
                    "detail": f"no residual {GUIDANCE_MARKER} markers in {claude_md.name}",
                })

    return report


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Prompt Library Verification Report")
    lines.append("")
    lines.append(f"CSV: `{report['csv_path']}`")
    lines.append(f"Brand: **{report['brand']}**")
    lines.append("")
    lines.append("## Hard Checks")
    for check in report["hard_checks"]:
        icon = "PASS" if check["passed"] else "FAIL"
        line = f"- [{icon}] **{check['name']}**"
        if check.get("detail"):
            line += f" - {check['detail']}"
        lines.append(line)
    overall = "ALL HARD CHECKS PASSED" if report["all_hard_passed"] else "AT LEAST ONE HARD CHECK FAILED"
    lines.append("")
    lines.append(f"**{overall}**")
    lines.append("")

    if report["soft_warnings"]:
        lines.append("## Soft Warnings")
        for w in report["soft_warnings"]:
            lines.append(f"- **{w['name']}**: {w['detail']}")
        lines.append("")

    d = report.get("distributions", {})
    if d:
        lines.append("## Distributions")
        lines.append(f"- **Total prompts**: {d.get('total_prompts')}")
        lines.append(f"- **Branded vs generic**: {d.get('branded_pct')}% branded ({d.get('branded_true')} rows) / {d.get('generic_pct')}% generic")
        lines.append("")
        lines.append("### Intent")
        for intent, (count, pct) in d.get("intent", {}).items():
            label = intent or "(blank)"
            lines.append(f"- {label}: {count} ({pct}%)")
        lines.append("")
        lines.append("### Segments")
        for seg, (count, pct) in d.get("segments", {}).items():
            lines.append(f"- {seg}: {count} ({pct}%)")
        lines.append("")
        lines.append("### Top 10 keywords by volume")
        for kw, vol in d.get("top_keywords", []):
            lines.append(f"- {kw}: {vol:,}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    try:
        intent_targets = parse_intent_targets(args.target_intent)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(3)

    claude_md = Path(args.claude_md) if args.claude_md else None
    brand_aliases = [a.strip() for a in (args.brand_aliases or "").split(",") if a.strip()]

    report = run_checks(
        csv_path=csv_path,
        brand=args.brand,
        target_count=args.target_count,
        intent_targets=intent_targets,
        claude_md=claude_md,
        brand_aliases=brand_aliases,
    )

    if args.output_format == "json":
        # Top keywords needs to be JSON-serializable
        if report.get("distributions", {}).get("top_keywords") is not None:
            report["distributions"]["top_keywords"] = [
                [kw, vol] for kw, vol in report["distributions"]["top_keywords"]
            ]
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    sys.exit(0 if report["all_hard_passed"] else 1)


if __name__ == "__main__":
    main()
