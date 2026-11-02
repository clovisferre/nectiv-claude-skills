#!/usr/bin/env python3
"""Convert a page's raw HTML into the markdown the analyzer expects.

Usage:
  curl -sL -A "Mozilla/5.0" "<url>" -o page.html
  python3 html_to_md.py page.html > page.md

Stdlib only, so the skill works without Firecrawl or any paid scraper. Keeps
headings (h1-h6 -> #), paragraphs, lists, tables (-> pipe tables), links and
bold. Drops nav, header, footer, aside, scripts, styles, forms and other site
chrome, and uses <article> or <main> when the page has one.
"""
import html
import re
import sys
from html.parser import HTMLParser

SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside",
        "form", "button", "iframe", "template", "select"}
BLOCK = {"p", "div", "section", "article", "main", "blockquote", "br", "hr"}


class Converter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf = [], []
        self.skip = 0
        self.list_stack, self.href = [], None
        self.table, self.row, self.cell = None, None, None

    # -- helpers ---------------------------------------------------------
    def flush(self, prefix=""):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self.out.append(prefix + text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "") + " " + (a.get("id") or "")
        if self.skip or tag in SKIP or re.search(r"\b(nav|menu|footer|sidebar|cookie|share|related|newsletter|subscribe|breadcrumb|toc|table-of-contents)\b", cls, re.I):
            if tag not in ("br", "hr", "img", "input", "meta", "link"):
                self.skip += 1
            return
        if tag == "br" and self.cell is not None:  # line breaks inside a table cell
            self._emit("; ")
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
        elif tag in BLOCK:
            self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            self.list_stack.append(tag)
        elif tag == "li":
            self.flush()
        elif tag == "table":
            self.flush()
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag == "a":
            self.href = a.get("href")
            self._emit("[")

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in ("br", "hr", "img", "input", "meta", "link"):
                self.skip -= 1
            return
        m = re.fullmatch(r"h([1-6])", tag)
        if m:
            self.flush("#" * int(m.group(1)) + " ")
        elif tag == "li":
            depth = max(0, len(self.list_stack) - 1)
            marker = "1." if self.list_stack and self.list_stack[-1] == "ol" else "-"
            self.flush("  " * depth + marker + " ")
        elif tag in ("ul", "ol"):
            self.flush()
            if self.list_stack:
                self.list_stack.pop()
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip().replace("|", "/"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            rows, self.table = self.table, None
            if rows:
                n = max(len(r) for r in rows)
                rows = [r + [""] * (n - len(r)) for r in rows]
                self.out.append("| " + " | ".join(rows[0]) + " |")
                self.out.append("|" + "---|" * n)
                self.out.extend("| " + " | ".join(r) + " |" for r in rows[1:])
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag == "a":
            self._emit(f"]({self.href})" if self.href and self.href.startswith("http") else "]")
            self.href = None
        elif tag in BLOCK:
            self.flush()

    def _emit(self, s):
        (self.cell if self.cell is not None else self.buf).append(s)

    def handle_data(self, data):
        if not self.skip:
            self._emit(data)


def main_content(raw):
    """Prefer <article>, then <main>, then <body>."""
    for tag in ("article", "main", "body"):
        m = re.search(rf"<{tag}\b[^>]*>(.*)</{tag}>", raw, re.S | re.I)
        if m:
            return m.group(1)
    return raw


def convert(raw):
    c = Converter()
    c.feed(main_content(raw))
    c.flush()
    md = "\n\n".join(c.out)
    md = re.sub(r"\*\*\s*\*\*", "", md)          # empty bold
    md = re.sub(r"\[\s*\]\([^)]*\)", "", md)     # empty links
    md = re.sub(r"\[([^\]]+)\](?!\()", r"\1", md)  # links without usable href
    # keep table rows and list items on consecutive lines
    md = re.sub(r"(\|[^\n]*\|)\n\n(?=\|)", r"\1\n", md)
    md = re.sub(r"(\n\s*(?:-|1\.) [^\n]+)\n\n(?=\s*(?:-|1\.) )", r"\1\n", md)
    md = re.sub(r"(\n\s*(?:-|1\.) [^\n]+)\n\n(?=\s*(?:-|1\.) )", r"\1\n", md)
    return html.unescape(md).strip() + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(convert(open(sys.argv[1], encoding="utf-8", errors="ignore").read()), end="")
