#!/usr/bin/env python3
"""Check a full rewritten article against the original before delivery.

Usage: python3 check_rewrite.py original.md revised.md

Enforces two rules:
1. Headings: the revised article has the same headings, in the same order and
   at the same levels. The only change allowed is rephrasing an existing
   heading as a question. Adding, removing, merging or splitting headings fails.
   One exception: a "Key Takeaways" heading may be added (house rule: 3-6
   bullets, first on the page under the H1), or its French name ("Points clés",
   "L'essentiel", "À retenir").
2. Coverage: every original sentence either survives (closely matched) in the
   revised article or is listed as rewritten/dropped, so you can confirm each
   one is covered by a proposed change and nothing was lost by accident.

Exit code 1 if the heading rule fails.
"""
import difflib
import re
import sys
import unicodedata

KT_RE = re.compile(r"key takeaways?|points? clés?|l['’]essentiel|à retenir", re.I)


def headings(md):
    return [(len(m.group(1)), m.group(2).strip())
            for m in re.finditer(r"(?m)^(#{1,6})\s+(.+)$", md)]


def prose_sentences(md):
    text = re.sub(r"(?m)^(#{1,6}\s.*|\s*\|.*)$", " ", md)  # drop headings, tables
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s*([-*+]|\d+[.)])\s+", "", text)
    text = re.sub(r"[*_`>]", "", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9\"'“«(])", re.sub(r"\s+", " ", text))
    return [p.strip() for p in parts if len(p.split()) >= 4]


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("’", "'"))  # keep accented letters' base
    return re.sub(r"[^a-z0-9 ]", "", s)


def main(orig_path, rev_path):
    orig = open(orig_path, encoding="utf-8").read()
    rev = open(rev_path, encoding="utf-8").read()
    ok = True

    ho, hr = headings(orig), headings(rev)
    orig_has_kt = any(KT_RE.search(t) for _, t in ho)
    added_kt = [] if orig_has_kt else [h for h in hr if KT_RE.search(h[1])]
    hr = [h for h in hr if h not in added_kt]
    print("HEADINGS")
    for h in added_kt:
        print(f"  allowed   added H{h[0]}: {h[1]!r} (Key Takeaways exception)")
    if len(ho) != len(hr):
        ok = False
        print(f"  FAIL: original has {len(ho)} headings, revised has {len(hr)}. "
              "Headings may only be rephrased, never added or removed.")
    for i, (a, b) in enumerate(zip(ho, hr)):
        if a == b:
            print(f"  same      H{a[0]}: {a[1]}")
        elif a[0] != b[0]:
            ok = False
            print(f"  FAIL      level changed H{a[0]}→H{b[0]}: {a[1]!r} → {b[1]!r}")
        elif b[1].rstrip().endswith("?"):
            print(f"  question  H{a[0]}: {a[1]!r} → {b[1]!r}")
        else:
            ok = False
            print(f"  FAIL      reworded but not a question: {a[1]!r} → {b[1]!r}")
    for extra in hr[len(ho):]:
        print(f"  FAIL      added H{extra[0]}: {extra[1]!r}")

    rs = [norm(s) for s in prose_sentences(rev)]
    print("\nCOVERAGE (original sentences not kept close to verbatim; confirm each is intentional)")
    missing = 0
    for s in prose_sentences(orig):
        best = max((difflib.SequenceMatcher(None, norm(s), r).ratio() for r in rs), default=0)
        if best < 0.8:
            missing += 1
            tag = "rewritten" if best >= 0.5 else "DROPPED?"
            print(f"  {tag:9} ({best:.2f}) {s[:150]}")
    if not missing:
        print("  every original sentence is present")
    print("\nRESULT:", "PASS" if ok else "FAIL (heading rule)")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
