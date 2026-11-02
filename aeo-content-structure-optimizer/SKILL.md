---
name: aeo-content-structure-optimizer
description: Audit and rewrite existing content (a live URL, a markdown/text draft, or pasted copy) to make it more likely to be cited by ChatGPT and other LLM answer engines, using findings from real citation data studies. Scores the page on front-loading, definitive language, question-style headings, chunk-friendly structure, HTML tables, content freshness, entity density, readability and analyst-voice tone, then returns prioritized, evidence-cited fixes and rewritten passages as a Google Doc: a before/after summary table at the top, then one section per change showing current text, suggested text and reasoning. Use this whenever someone asks to optimize content for AI search, AEO, GEO, LLM visibility, ChatGPT citations or "getting cited by AI", or to review a blog post or page for AI-readiness, even if they don't say "citation".
version: 0.9.0
---

# AEO Content Structure Optimizer

Turn a page written for "keep the human scrolling" into one an LLM can lift
answers from. Every recommendation has to trace back to a measured finding in
`references/evidence.md`. That evidence is what makes this a Nectiv
deliverable rather than generic AEO advice, so always cite the factor ID
(e.g. `[POS-DOC]`) and the stat behind it.

## Workflow

### 1. Get the content as markdown
- **URL:** fetch the raw HTML with `curl`, then convert it with the bundled
  script. Neither needs a paid scraper or any extra connector:
  ```
  curl -sL -A "Mozilla/5.0" "<url>" -o page.html
  python3 <skill-dir>/scripts/html_to_md.py page.html > page.md
  ```
  The converter keeps headings, lists, tables and links, drops nav/footer
  chrome, and prefers `<article>`/`<main>`. Skim `page.md` and delete any
  leftover chrome (breadcrumbs, byline, promo blocks) so it doesn't skew
  positional stats. Keep `page.html`: the analyzer reads it to count real
  `<table>` elements [TABLE] and to find `dateModified`/`datePublished` in
  schema and meta tags [FRESH].
  If `curl` is blocked (403, bot wall, JavaScript-only page), use your
  environment's page-fetch tool (`WebFetch` in Claude Code), asking for the
  full article text verbatim with headings marked as `#`/`##`, and skip the
  `--html` checks. If that fails too, ask the user to paste the article.
- Note the page's **industry** and **query intent** (commercial vs.
  informational). Both set the freshness window it's judged against.
- **File / pasted text:** save as `page.md`. Keep heading markup (`##`) intact,
  because the heading analysis depends on it. If pasted text has no markdown
  but obvious headings, add `##` to them.
- Note the page's **target query/topic**. If it isn't obvious from the
  H1/title, infer it and state your assumption.

### 2. Measure
Run `python3 <skill-dir>/scripts/analyze.py page.md --html page.html`
(leave out `--html` for drafts and pasted text). It returns JSON keyed by
factor ID: positional bands, first definitive sentence position, intro
fluff, per-heading Q/A + entity-echo checks, tables, freshness (metadata
dates, visible "last updated" label, days since update, out-of-date year
references), entity density, FK grade, long sentences, and subjectivity (if
TextBlob is installed).

The script's numbers are heuristics. Entity density in particular is an
approximate proper-noun count. Use them to spot problems and to compare
before/after, and use your own reading to confirm. Never report a heuristic
number as if it were an exact measurement against the study benchmark.

### 3. Read `references/evidence.md`, then diagnose
Judge each factor against its benchmark. Things the script can't see that you
must judge by reading:
- **Is the key insight actually in the first ~20–30%?** The script only finds
  definitive sentences. You decide whether the *most valuable* claim (the
  thing a user would ask ChatGPT about) is up top or buried.
- **Information gain per sentence.** Citations come mostly from mid-paragraph
  sentences [POS-PARA], so the issue is rarely position inside a paragraph. It
  is whether any sentence in the paragraph is complete, specific and quotable
  on its own.
- **Entity gaps** [ENTITY]. Read every generic reference and every
  entity-free sentence the analyzer lists, and note which named entity
  would make each one specific and checkable. Pages usually sit near the
  5–8% baseline against 20.6% for cited text, so this is normally one of
  the top two fixes. Rate the page Weak if overall density is under 8% or
  more than 40% of sentences name no entity.
- **Tone.** Is it dry fact-listing, hype, or the analyst voice (fact + what it
  means) [SUBJ]?
- **Chunk self-containment** [CHUNK]. AI retrieval scores chunks of about
  75 words, not whole pages. Imagine cutting each section out and pasting
  it somewhere else. Does it still say what it's about and answer the
  question on its own? Look at the analyzer's long paragraphs, sections over
  300 words with no subheadings, and section openers that start with a
  pronoun ("It…", "This…").
- **Key Takeaways** [TAKEAWAYS]. Check the analyzer's `TAKEAWAYS` result.
  The page needs a section headed "Key Takeaways" with 3–6 bullets as the
  **first thing on the page**: directly under the H1 title, above the
  introduction. Flag it if it's missing, sits anywhere below the intro, has
  fewer than 3 or more than 6 bullets, or is written as prose. Cite why: 44.2% of
  ChatGPT citations come from the first 30% of a page [POS-DOC].
- **Page type.** Is this comparison/roundup/pricing/"best X" content? If so,
  a missing table near the top is a high-priority gap [TABLE]. On
  informational or how-to pages the table evidence is weak, so suggest a
  table only where the content is already tabular (specs, steps with
  attributes, pros/cons), and say that the evidence there is thinner.
- **Freshness** [FRESH]. Compare days since update against the window for
  the page's intent and industry (see FRESH-WINDOW in `evidence.md`). Then
  look for content that has actually gone stale: last year in the title
  ("Best X 2024"), outdated pricing, discontinued products, old stats
  presented as current. A cited 2024 study isn't stale by itself, but "the
  latest data (2023)" is. Check that the visible date and the schema
  `dateModified` both exist and agree. For drafts, skip the date checks and
  only flag stale references.

### 3b. Find data for the 2–3 key points
Original statistics are the most citable thing a page can have: each one is
a named, dated, checkable entity [ENTITY]. Use the native search and fetch
tools of whatever environment you're running in (`WebSearch` and `WebFetch`
in Claude Code; the built-in web search in other assistants). Don't rely on
a paid connector, since teammates may not have it.

1. **Pick 2–3 key points.** Choose the claims a reader would most want
   backed by data. Start with any number the page states without a source,
   then the page's central claims (ROI, adoption, cost, time saved). Skip
   points where no credible research is likely to exist.
2. **Search for primary research.** Run 1–2 searches per point, aiming for
   the original publisher: analyst firms (Gartner, Forrester), research
   bodies, government data, a vendor's own published study with a stated
   sample. Prefer the last 2–3 years. Statistic roundup pages ("100 ABM
   stats") are useful only as leads to the original.
3. **Verify on the source page.** Open the primary source with the fetch
   tool and ask for the exact sentence, the publication date and the
   sample size, quoted verbatim. **Search-result summaries paraphrase and
   often misquote** (in testing, one turned Forrester's "most commonly
   21–50%" into "most respondents"), so a figure only counts once you've
   seen it on the source page. If the publisher's page is unreachable or
   paywalled, use a statistic only if a press release or abstract from that
   publisher states it, and say so.
4. **Write it in.** Integrate each verified figure into the paragraph it
   supports, as a definitive sentence: number, what it measures, publisher,
   year, sample if short, and a link ("…according to a 2025 Gartner survey
   of 632 B2B buyers"). Quote the figure exactly as the source states it. Don't
   round it up or turn "most commonly" into "most".
5. **Audit the page's existing statistics** while you're there. For each
   number already on the page, flag it if (a) you can't trace it to a
   primary source, (b) the source says something different (correct it),
   or (c) newer data contradicts it. Recommend replacing untraceable
   figures with verified ones rather than leaving them in.
6. **Record sources** in `audit.json` under `sources` (title, publisher,
   date, URL, the exact figure used). They appear in the Doc so the client
   can check each one.

Deliver this as its own change ("Add verified data to the key points"),
with `pairs` showing the current sentence and the sentence with the
statistic added, plus a note on what the source is. If a statistic
contradicts something the page claims, say so in the note. Don't quietly
rewrite the client's claim to fit.

### 4. Prioritize
Rank fixes by the factor priority at the bottom of `evidence.md` (bigger
measured effect → higher priority), adjusted for how badly the page misses.
A page that already front-loads well shouldn't lead with a POS-DOC fix.
Limit the list to the fixes that matter. Seven sharp fixes beat twenty
nitpicks.

### 5. Rewrite
Produce the changes for the highest-impact fixes, then the **complete
article in its final state** with every change applied.

**Heading rule (strict).** Keep the article's headings exactly as they
are: same number, same order, same levels. The only heading change you may
suggest is rewording an existing heading as a question. Never add, remove,
split or merge headings. **One exception:** add a "Key Takeaways" heading
when the page has none (change 2 below). Summary labels like "In Brief" or "Bottom Line" can
stay as they are. To break up a long section without new headings, use
paragraphs that open with a bold lead-in naming their subject
("**IP geolocation errors.** IP geolocation is…"), plus lists.

The usual changes:
1. **Opening summary.** Open with the direct answer, name concrete
   entities, define the core term ("X is Y"), and cut throat-clearing.
2. **Key Takeaways** [TAKEAWAYS]. Make sure the page has a section headed
   "Key Takeaways" with 3–6 bullets as the first thing on the page:
   directly under the H1 title, before the introduction. If the page has a
   Key Takeaways section lower down, move it to the top. Each bullet is a complete, definitive claim that could be quoted
   alone, with the page's own entities and numbers, never a teaser. Pull
   every bullet from facts the article states. If a prose summary already
   sits at the top ("In Brief", "TL;DR"), convert it rather than adding a
   duplicate. The introduction follows the takeaways, so keep it from
   repeating bullet 1 word for word. In the Why, cite: 44.2% of ChatGPT citations come from the
   first 30% of a page, and bullets are self-contained chunks
   [POS-DOC][CHUNK]. Say that the 3–6 count is a Nectiv house rule.
3. **Question headings.** Reword abstract existing headings as literal user
   questions, and make the first words of the answer under each one repeat
   the heading's subject ("When did SEO start?" → "SEO started in…").
4. **Definitive language** [DEFINITIVE]. A sentence-by-sentence pass, not
   a general note:
   - Start from the analyzer's `DEFINITIVE.rewrite_candidates` (hedges,
     vague quantifiers, indirect openers like "There are…", abstract verbs
     like "lies within" or "is a critical component of"), then read for
     anything it missed.
   - List the page's key terms: the target query's subject, every concept
     in the headings, product and feature names. Each needs one
     subject-first "X is Y" sentence near its first mention. Add any
     definition that's missing.
   - Rewrite each candidate as a direct claim: subject first, "is/are",
     the specific relationship, numbers where the page has them ("several
     reasons" → "three causes").
   - **Never overclaim.** Remove a hedge only when the page's own facts
     support the firmer claim. Keep hedges that are true ("can be
     assigned" when it happens only sometimes), and list them under
     "Left as is, for accuracy". Mark any firmer claim the client must
     confirm.
   - Deliver these as `pairs` (current sentence, rewritten sentence, a
     one-line note on what changed) in a single "Make key claims
     definitive" change.
5. **Restructure dense prose** [CHUNK]. Split paragraphs over 120 words,
   turn embedded series ("X, Y, and Z each do…") into lists, use bold
   lead-ins instead of new headings, and rewrite pronoun-led openers so
   they name their subject. Keep each answer within ~75 words of the
   heading that asks it [POS-PARA].
6. **Name names: entity density** [ENTITY]. This is a high-weight change.
   It's the largest measured gap in the evidence (cited text 20.6% vs 5–8%
   for normal English, about 3x), and most pages miss it badly. Give it
   the same sentence-by-sentence treatment as definitive language, as its
   own change with `pairs`:
   - **Where to look:** the analyzer's `ENTITY.generic_references` ("many
     tools", "third-party databases", "studies show", "the platform") and
     `ENTITY.zero_entity_sentences`. Start with the intro, the Key
     Takeaways and the first sentence under each heading, since those are
     the most-cited zones [POS-DOC].
   - **What counts as an entity:** brands and products (including
     competitors), named features and settings, standards and protocols,
     organizations, people, places, named reports and studies, years and
     dates, and specific numbers with units.
   - **Where entities come from, in order:** (1) entities the page already
     names elsewhere (`ENTITY.entities_on_page`); repeat them instead of
     "it" or "the platform". (2) Well-known facts you're confident of, such
     as a product's former name ("Microsoft Ads, formerly Bing Ads") or the
     standard name for a feature. (3) The client's own data: proprietary
     stats, customer counts, named case studies. (4) Otherwise a specific
     bracketed placeholder saying what to supply: `[name the
     geolocation provider, e.g. a vendor Microsoft documents]`, `[add the
     % of flagged clicks from data-center IPs]`. Never invent a brand,
     number or study. A made-up entity hurts the client more than a vague
     sentence does.
   - **Targets** (heuristic count, directional): density at least 12%
     overall and 15% in the intro and Key Takeaways, and no more than 25%
     of sentences with no entity. Report both before and after, and count
     the entities added and the placeholders left for the client.
   - Don't stuff entities. Every name has to belong in the sentence and be
     accurate. A list of logos isn't the goal; a checkable, specific claim
     is.
7. **Summary table** (comparison-type pages, or content that's naturally
   tabular). Put it near the top, one row per option, every cell pulled
   from the page, placeholders for anything missing. Tell the user to
   publish it as a real HTML `<table>`, not an image or styled divs.
8. **Freshness update list.** For pages outside their window, list the
   specific updates that would make a refresh real: stats to replace,
   pricing or product changes to verify, examples to modernize, title year
   to change. Then recommend a visible "Last updated" date plus a matching
   schema `dateModified`. A date bump with no content changes is not a
   refresh. Suggest a review cadence that matches the page's window.
9. **Summary section.** If the article has a closing summary section, make
   its takeaways quotable (e.g. a short list). Don't add a new heading for
   one.
10. **Sentence simplification.** Simplify only sentences that are genuinely
   winding (>35 words, stacked clauses). Keep business-grade vocabulary
   [READ]. The goal is Economist/HBR, not grade 6.

Preserve the author's facts, claims, examples, callouts (pro tips, CTAs)
and brand voice. Restructure and sharpen, but don't change what the page
asserts.

**Final article.** Write `page_final.md`: the entire article (title,
every heading, every paragraph, lists, callouts, the closing CTA) with
every proposed change applied. Leave out only site chrome (nav, author
box, footer promos). Then run:

`python3 <skill-dir>/scripts/check_rewrite.py page.md page_final.md`

It must print `RESULT: PASS` (the heading rule). Go through its coverage
list: every original sentence marked "rewritten" or "DROPPED?" has to be
covered by a proposed change. If one isn't, you lost content by accident,
so put it back.

### 6. Re-measure
Rerun the analyzer on `page_final.md` and use the before → after numbers
in the summary table. Report honestly when a metric gets worse. With the
heading rule, section length often goes up, so say why in that row's note.

### 7. Deliver the Google Doc
The client deliverable is a Google Doc laid out like this:
1. **Summary paragraph** (conclusion first), then a **before/after summary
   table**: one row per structural metric (question headings, paragraphs
   over 120 words, sections over 300 words, average section length,
   lists/tables, FK grade), with the current value, the value with the
   changes applied, and which changes drive it. Always include the three
   entity rows near the top of the table: overall entity density,
   intro/Key Takeaways entity density, and sentences with no entity. Add a
   row for "named entities added / placeholders for the client to fill",
   so the client can see how much of the gain depends on their input.
2. **Proposed changes.** Each change gets its own heading ("Change N:
   <imperative label>"), then where it is on the page, the **current
   text** (quoted exactly, in italics), the **suggested change** directly
   underneath as ready-to-paste paragraphs and lists (or a table, for a
   table change), and the **Why** (factor ID + stat) last. Don't put the
   changes themselves in a table, because writers need to read and copy
   them as normal text.
3. Technical fixes, then the scorecard.
4. **Revised article (final version):** the full `page_final.md`, after a
   divider line.

Styling (navy table headers, shaded current/suggested boxes, colored
statuses, spacing) comes from `build_doc.py`. Don't hand-write HTML.

1. Write `audit.json` in the scratchpad (schema in the docstring of
   `scripts/build_doc.py`). In `changes[].after`, write the replacement text
   ready to paste. Separate paragraphs with blank lines, use `[…]` to skip
   unchanged sentences, write new headings as `Heading: <text>`, and start
   list items with `• ` or `1. ` (they become real Doc lists). Quote
   `before` text from the page exactly. Give each `metrics` row a
   `changes` value naming the changes that move it, and a `note` when a
   metric moves the wrong way. Set `final_article_md` to `page_final.md`.
2. `python3 <skill-dir>/scripts/build_doc.py audit.json > audit.html`
3. Load the `google-workspace` skill, then call Google Drive `create_file`
   with `contentMimeType: "text/html"`, the HTML as `textContent`, and a
   title like `ChatGPT Citation Audit – <Client>: <page topic>`. Drive
   converts it into a native Doc with real headings, lists and tables.
4. Check the result with Drive `read_file_content`: the summary table
   should come first, then one heading per change, and the final article
   should be complete. If you can run code, export a PDF
   (`download_file_content`, `exportMimeType: "application/pdf"`) and look
   at a few pages. Swift's PDFKit can render pages to PNG on macOS. Then give the user the Doc link.

Write the Doc for the client, not for Nectiv: no emoji, statuses written as
Strong / Needs work / Weak, and no description of how the audit was run.
If Google Drive isn't connected, still build `audit.html` and tell the user
where it is. Uploading that file to Google Drive (New > File upload, then
Open with > Google Docs) produces the same formatted Doc. Mention that
connecting "claude.ai Google Drive" via `/mcp` lets you create the Doc
directly next time.

## Output format

```
# ChatGPT Citation Audit: <page title>
**URL / source:** …   **Target query:** …   **Overall:** <Strong | Needs work | Weak>

## Scorecard
| Factor | This page | Benchmark (cited content) | Status |
|---|---|---|---|
| Front-loading [POS-DOC] | first definitive claim at X%; intro entity density Y% | 44% of citations from first 30% | 🔴/🟡/🟢 |
| Definitive language [DEFINITIVE] | … | 36.2% vs 20.2% | |
| Key Takeaways [TAKEAWAYS] | present? position %, bullet count | 3–6 bullets, first on the page; 44.2% of citations from first 30% | |
| Question headings + echo [QA] | … | 2x; 78% of Q citations from headings | |
| Chunk structure [CHUNK] | long paras, unbroken sections, pronoun openers, list use | controlled test: Q&A > structured >> dense prose | |
| HTML table [TABLE] | count, first at X%; page type | 30% of cited pages vs 13% of Google (2.3x) | |
| Freshness [FRESH] | updated N days ago; window for intent/industry; stale refs | commercial: 60% of cited <6mo; SaaS window ~3mo | |
| Entity density [ENTITY] | … | 20.6% vs 5–8% baseline | |
| Readability [READ] | FK … | 16 vs 19.1 | |
| Analyst voice [SUBJ] | … | ~0.47 | |
| Summary section [POS-DOC] | yes/no | conclusion zone = 24.7% | |

## Priority fixes
1. **<fix>** [FACTOR-ID]: why (one line with the stat). Where: <section>.
…

## Rewrites
### Intro: before / after
### Headings: before → after (table)
### Other passages: before / after

## Before → after metrics
```

Keep the scorecard honest. A 🟢 is fine. Don't invent problems to fill the
list.

## Adding new studies
When you supply another study, add it to `references/evidence.md` as a
new "Study N" section using the same structure (source, dataset, findings
with IDs, caveats). Record any disagreements under "Conflicts & open
questions", then update the factor priority list. If a new finding is
mechanically measurable, extend `scripts/analyze.py` with a new factor key.
