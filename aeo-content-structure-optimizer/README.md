# AEO Content Structure Optimizer (Claude Code skill)

Audits an existing page and rewrites it to be more likely to be cited by
ChatGPT and other AI answer engines. Every recommendation is tied to a
measured finding from real citation studies (see `references/evidence.md`).
The deliverable is a Google Doc with a before/after summary table, one
section per proposed change (current text → suggested text → why), verified
sources, and the full revised article.

## Install

```bash
git clone https://github.com/Nectiv-Digital/nectiv-claude-skills.git
cp -R nectiv-claude-skills/aeo-content-structure-optimizer ~/.claude/skills/
```

Restart Claude Code. The skill triggers on requests like "optimize this page
for ChatGPT citations", "AEO audit of <url>" or "make this post more likely
to be cited by AI".

## Requirements

- Python 3 (standard library only) and `curl`.
- Web search and fetch: Claude Code's built-in `WebSearch` and `WebFetch`.
  No paid scraper is needed.
- Optional: the "claude.ai Google Drive" connector (`/mcp`) to create the
  Doc directly. Without it the skill writes `audit.html`, which you can upload
  to Google Drive and open with Google Docs.

## What's inside

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow and rules Claude follows |
| `references/evidence.md` | The citation studies, factor IDs, caveats and priority order |
| `scripts/html_to_md.py` | Converts a page's raw HTML into markdown for analysis |
| `scripts/analyze.py` | Measures the page against each factor |
| `scripts/check_rewrite.py` | Enforces the heading rule and checks nothing was lost in the rewrite |
| `scripts/build_doc.py` | Builds the styled Google Doc (HTML) from the audit |

## Adding a study

Paste the study into Claude with the skill loaded and ask to add it. It goes
into `references/evidence.md` as a new "Study N" section with its findings,
caveats and any conflicts, and the factor priority is updated.
