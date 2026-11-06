#!/usr/bin/env python3
"""Build the client-facing Google Doc (as HTML for Drive upload) from an audit.

Usage: python3 build_doc.py audit.json > audit.html

Upload the HTML with Google Drive `create_file` (contentMimeType "text/html").
Drive converts headings, paragraphs, lists, links, tables, cell shading and
text colors into native Docs formatting.

audit.json:
{
  "lang": "en | fr",   # optional, default "en": language of the doc's fixed labels
  "title": "...", "url": "...", "target_query": "...", "date": "YYYY-MM-DD",
  "overall": "Strong | Needs work | Weak",
  "summary": "Conclusion-first paragraph: what to change and why.",
  "metrics": [   # summary table at the top of the doc
    {"metric": "Question headings", "before": "1 of 5", "after": "3 of 5",
     "changes": "Change 3", "note": "optional caveat"}
  ],
  "changes": [   # one heading per change, in priority order
    {"title": "Rewrite the opening summary",      # short imperative label
     "section": "In Brief",                       # where on the page
     "before": "exact current text; […] for omitted parts",
     "after": "replacement text (markdown: blank lines split paragraphs,
               '- ' / '1. ' lists, '|' tables, **bold**, [links](url))",
     "why": "reasoning with factor ID + stat",
     # optional, instead of before/after: sentence-level rewrites
     "pairs": [{"before": "...", "after": "...", "note": "what changed"}],
     "kept": ["hedges deliberately left in place, with the reason"]}
  ],
  "other": ["technical / non-content recommendations"],
  "sources": [   # verified statistics added in step 3b
    {"figure": "exact figure as used", "title": "...", "publisher": "...",
     "date": "Mon YYYY", "url": "https://..."}
  ],
  "scorecard": [{"factor": "...", "page": "...", "benchmark": "...", "status": "Strong|Needs work|Weak"}],
  "final_article_md": "path/to/page_final.md"   # full article with all edits applied
}
"""
import html
import json
import re
import sys

NAVY = "#1a2b4c"
GRAY = "#5f6368"
BORDER = "#d0d7de"
STATUS_COLOR = {"strong": "#188038", "needs work": "#b06000", "weak": "#c5221f",
                "fort": "#188038", "à travailler": "#b06000", "faible": "#c5221f"}
# French labels are a local addition to the Nectiv original.
LABELS = {
    "en": {
        "html_lang": "", "statuses": {},
        "page": "Page:", "query": "Target query:", "date": "Audit date:", "overall": "Overall:",
        "summary": "Summary of changes: before and after",
        "metric_cols": ["Metric", "Current page", "With changes", "Driven by"],
        "changes": "Proposed changes", "change": "Change {n}:", "where": "Where:", "rewrite": "Rewrite {k}:",
        "kept": "Left as is, for accuracy:", "current": "Current text", "suggested": "Suggested change",
        "why": "Why:", "other": "Technical fixes", "sources": "Sources for added data",
        "source_cols": ["Figure used", "Source", "Published"], "scorecard": "Scorecard",
        "score_cols": ["Factor", "This page", "Benchmark (cited content)", "Status"],
        "final": "Revised article (final version)",
        "final_note": "The complete article with every proposed change applied. "
                      "Bracketed items are facts to supply or verify before publishing.",
    },
    "fr": {
        "html_lang": " lang='fr'",
        "statuses": {"strong": "Fort", "needs work": "À travailler", "weak": "Faible"},
        "page": "Page :", "query": "Requête cible :", "date": "Date de l'audit :", "overall": "Appréciation générale :",
        "summary": "Résumé des modifications : avant et après",
        "metric_cols": ["Indicateur", "Page actuelle", "Après modifications", "Modifications concernées"],
        "changes": "Modifications proposées", "change": "Modification {n} :", "where": "Emplacement :",
        "rewrite": "Réécriture {k} :", "kept": "Conservé tel quel, par souci d'exactitude :",
        "current": "Texte actuel", "suggested": "Modification proposée",
        "why": "Pourquoi :", "other": "Corrections techniques", "sources": "Sources des données ajoutées",
        "source_cols": ["Chiffre utilisé", "Source", "Publication"], "scorecard": "Tableau d'évaluation",
        "score_cols": ["Critère", "Cette page", "Repère (contenus cités)", "État"],
        "final": "Article révisé (version finale)",
        "final_note": "L'article complet, avec toutes les modifications proposées. "
                      "Les éléments entre crochets sont des faits à fournir ou à vérifier avant publication.",
    },
}
L = LABELS["en"]


def inline(text):
    """Escape, then apply the markdown subset we emit: **bold**, *italic*, [links](url)."""
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t


def status(s):
    s = L["statuses"].get(str(s).strip().lower(), s)
    c = STATUS_COLOR.get(str(s).strip().lower())
    return f'<span style="color:{c}"><b>{html.escape(str(s))}</b></span>' if c else inline(str(s))


# Google Docs' HTML import honors class rules in a <style> block (verified),
# which keeps the upload small compared with repeating inline styles.
CSS = f"""
body{{font-family:Arial}}
p{{margin-top:0;margin-bottom:8pt}} p.rw{{margin-top:14pt}}
h1{{color:{NAVY}}} h2{{color:{NAVY};margin-top:20pt}} h3{{margin-top:16pt}}
h4{{font-size:13pt;color:{NAVY}}} h5{{font-size:12pt;color:#000000;font-weight:bold}}
table{{border-collapse:collapse;width:100%}}
td.th{{background-color:{NAVY};border:1px solid {NAVY};padding:6px;color:#ffffff;font-weight:bold;vertical-align:top}}
td.d{{border:1px solid {BORDER};padding:6px;vertical-align:top}}
td.cur{{background-color:#f4f5f7;border:1px solid #f4f5f7;border-left:4px solid #9aa0a6;padding:8px;vertical-align:top}}
td.sug{{background-color:#edf7ee;border:1px solid #edf7ee;border-left:4px solid #34a853;padding:8px;vertical-align:top}}
td.sum{{background-color:#eef3fb;border:1px solid #eef3fb;border-left:4px solid {NAVY};padding:8px;vertical-align:top}}
.g{{color:{GRAY}}} .sm{{font-size:9pt}} .meta{{color:{GRAY};font-size:10pt}}
.lab-cur{{color:{GRAY};font-weight:bold;font-size:9pt}} .lab-sug{{color:#188038;font-weight:bold;font-size:9pt}}
"""


def table(headers, rows, raw_cols=()):
    """Data table: navy header row, light borders. raw_cols = column indexes
    whose cells are already HTML."""
    out = ["<table><tr>"]
    out += [f'<td class="th">{html.escape(h)}</td>' for h in headers]
    out.append("</tr>")
    for r in rows:
        cells = [(str(c) if i in raw_cols else inline(str(c))) for i, c in enumerate(r)]
        out.append("<tr>" + "".join(f'<td class="d">{c}</td>' for c in cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def callout(inner_html, cls):
    """Single-cell shaded box with a colored left bar (cls: cur, sug, sum)."""
    return f'<table><tr><td class="{cls}">{inner_html}</td></tr></table>'


def label(text, cls):
    return f'<p><span class="{cls}">{html.escape(text.upper())}</span></p>'


def md_to_html(md, demote=0):
    """Markdown → HTML: headings (demoted), paragraphs, lists, pipe tables."""
    out, lines, i = [], md.split("\n"), 0
    list_re = r"^\s*([-*+•]|\d+[.)])\s+"
    while i < len(lines):
        line = lines[i].rstrip()
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if not line.strip():
            i += 1
        elif m:
            lvl = min(len(m.group(1)) + demote, 6)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
        elif line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(table(rows[0], rows[1:]))
        elif re.match(list_re, line):
            tag = "ol" if re.match(r"^\s*\d", line) else "ul"
            items = []
            while i < len(lines) and re.match(list_re, lines[i]):
                items.append(re.sub(list_re, "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|\s*\|)", lines[i]) \
                    and not re.match(list_re, lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def current_box(text):
    paras = "".join(f"<p><i>{inline(x)}</i></p>" for x in str(text).split("\n") if x.strip())
    return callout(paras, "cur")


def suggested_box(md):
    return callout(md_to_html(str(md)), "sug")


def why(text):
    return f'<p><span class="g"><b>{L["why"]}</b> {inline(text)}</span></p>'


def build(a):
    global L
    lang = a.get("lang", "en")
    if lang not in LABELS:
        sys.exit(f"Unknown lang {lang!r}: use one of {sorted(LABELS)}")
    L = LABELS[lang]
    h = [f"<html{L['html_lang']}><head><meta charset='utf-8'><title>{html.escape(a['title'])}</title>"
         f"<style>{CSS}</style></head><body>",
         f'<h1>{inline(a["title"])}</h1>']
    meta = []
    if a.get("url"):
        meta.append(f'<b>{html.escape(L["page"])}</b> <a href="{html.escape(a["url"])}">{html.escape(a["url"])}</a>')
    if a.get("target_query"):
        meta.append(f"<b>{html.escape(L['query'])}</b> {inline(a['target_query'])}")
    if a.get("date"):
        meta.append(f"<b>{html.escape(L['date'])}</b> {inline(a['date'])}")
    if a.get("overall"):
        meta.append(f"<b>{html.escape(L['overall'])}</b> {status(a['overall'])}")
    if meta:
        h.append('<p><span class="meta">' + "<br>".join(meta) + "</span></p>")
    if a.get("summary"):
        h.append(callout(f"<p>{inline(a['summary'])}</p>", "sum"))

    if a.get("metrics"):
        h.append(f"<h2>{html.escape(L['summary'])}</h2>")
        rows = []
        for m in a["metrics"]:
            after = f"<b>{inline(str(m.get('after', '')))}</b>"
            if m.get("note"):
                after += f'<br><span class="g sm">{inline(m["note"])}</span>'
            rows.append([inline(str(m.get("metric", ""))), inline(str(m.get("before", ""))), after,
                         inline(str(m.get("changes", "")))])
        h.append(table(L["metric_cols"], rows, raw_cols=(0, 1, 2, 3)))

    h.append(f"<h2>{html.escape(L['changes'])}</h2>")
    for n, c in enumerate(a["changes"], 1):
        h.append(f"<h3>{html.escape(L['change'].format(n=n))} {inline(c.get('title') or c.get('section', ''))}</h3>")
        if c.get("section"):
            h.append(f'<p><span class="meta"><b>{html.escape(L["where"])}</b> {inline(c["section"])}</span></p>')
        if c.get("pairs"):
            for k, p in enumerate(c["pairs"], 1):
                note = f" {inline(p['note'])}" if p.get("note") else ""
                h.append(f'<p class="rw"><b>{html.escape(L["rewrite"].format(k=k))}</b>{note}</p>')
                h.append(current_box(p["before"]))
                h.append(suggested_box(p["after"]))
            if c.get("kept"):
                h.append(f'<p><span class="g"><b>{html.escape(L["kept"])}</b></span></p>')
                h.append("<ul>" + "".join(f'<li><span class="g">{inline(x)}</span></li>'
                                          for x in c["kept"]) + "</ul>")
        else:
            h.append(label(L["current"], "lab-cur"))
            h.append(current_box(c.get("before", "")))
            h.append(label(L["suggested"], "lab-sug"))
            h.append(suggested_box(c.get("after", "")))
        if c.get("why"):
            h.append(why(c["why"]))

    if a.get("other"):
        h.append(f"<h2>{html.escape(L['other'])}</h2><ul>" + "".join(f"<li>{inline(x)}</li>" for x in a["other"]) + "</ul>")
    if a.get("sources"):
        h.append(f"<h2>{html.escape(L['sources'])}</h2>")
        h.append(table(L["source_cols"],
                       [[inline(s.get("figure", "")),
                         f'<a href="{html.escape(s.get("url", ""))}">{inline(s.get("title", ""))}</a>'
                         + (f'<br><span class="g sm">{inline(s.get("publisher", ""))}</span>' if s.get("publisher") else ""),
                         inline(s.get("date", ""))] for s in a["sources"]], raw_cols=(0, 1, 2)))
    if a.get("scorecard"):
        h.append(f"<h2>{html.escape(L['scorecard'])}</h2>")
        h.append(table(L["score_cols"],
                       [[inline(s.get("factor", "")), inline(s.get("page", "")), inline(s.get("benchmark", "")),
                         status(s.get("status", ""))] for s in a["scorecard"]], raw_cols=(0, 1, 2, 3)))
    if a.get("final_article_md"):
        h.append("<hr>")  # Docs' HTML import ignores CSS page breaks (tested); a rule marks the switch
        h.append(f"<h2>{html.escape(L['final'])}</h2>")
        h.append(f'<p><span class="g">{html.escape(L["final_note"])}</span></p>')
        h.append(md_to_html(open(a["final_article_md"], encoding="utf-8").read(), demote=2))
    h.append("</body></html>")
    return "\n".join(h)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")  # the HTML declares utf-8, whatever the console uses
    print(build(json.load(open(sys.argv[1], encoding="utf-8"))))
