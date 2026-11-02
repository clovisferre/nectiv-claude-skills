# Evidence base: what makes content get cited by ChatGPT

Every recommendation the skill makes must trace back to a finding in this file.
Add new studies as new sections; when studies conflict, record the conflict in
the "Conflicts & open questions" section rather than silently overwriting.

All findings below are **correlational** (cited vs. non-cited text), not
controlled experiments. Treat them as strong priors, not laws.

---

## Study 1 — "Ski ramp" study (1.2M verified ChatGPT citations)

- **Source:** Kevin Indig, Growth Memo, "The science of how AI pays attention" (Feb 16, 2026):
  https://www.growth-memo.com/p/the-science-of-how-ai-pays-attention
  (public coverage: https://searchengineland.com/chatgpt-citations-content-study-469483)
- **Dataset:** 1.2M verified ChatGPT citations; positional analysis on 18,012
  citations; paragraph-level analysis on 1,000 heavily-cited pages. Validated
  with 4 randomized splits (batch 1 slightly flatter; 2–4 near-identical).
- **Method notes:** subjectivity measured on the standard NLP 0–1 scale
  (TextBlob-style); readability via Flesch-Kincaid grade; entity density =
  share of tokens that are proper nouns (brands, tools, people).

### F1.1 Position in document — the "ski ramp"  [ID: POS-DOC]
| Section of page | Share of citations |
|---|---|
| First 30% (intro) | **44.2%** |
| 30–70% (middle) | 31.1% |
| Last 30% (conclusion) | 24.7% |
- Content in the middle is ~2.5x less likely to be cited than intro content.
- Footer (90–100%) drops off sharply, but a **Summary/Conclusion section just
  before the footer** gets cited.
- Practical read: highest citation odds are paragraphs in the **first ~20%**.
- Implication: lead with the key insight (BLUF); don't save the best material
  for paragraph 12; add a real summary section at the end.

### F1.2 Position in paragraph  [ID: POS-PARA]
| Sentence position | Share |
|---|---|
| Middle sentences | **53%** |
| First sentence | 24.5% |
| Last sentence | 22.5% |
- ChatGPT reads paragraphs fully and picks the sentence with the highest
  "information gain" (most complete, entity-rich, additive).
- Implication: **don't** force every paragraph into answer-first-sentence
  shape. Optimize sentence quality, not sentence position, inside paragraphs.

### F1.3 Definitive language  [ID: DEFINITIVE]
- Cited text contains definitive language **36.2% vs 20.2%** (≈1.8x).
- Patterns: "X is…", "is defined as", "refers to", "means" — clear
  subject→definition/relationship statements. Doesn't have to be a literal
  definition, but the relationship between concepts must be explicit.
- Bad: "In this fast-paced world, automation is becoming key..."
  Good: "Demo automation is the process of using software to..."

### F1.4 Conversational Q→A structure  [ID: QA]
- Cited text is **2x** more likely to contain a question mark (18% vs 8.9%).
- **78.4%** of cited question-containing text comes from **headings**: the H2
  acts as the user prompt; the paragraph right after acts as the answer.
- "Entity echoing": the heading's subject is repeated as the first words of
  the answer. `<h2>When did SEO start?</h2><p>SEO started in…</p>`
- Loser: abstract topic headings ("The History of SEO") followed by
  narrative ("It began in the early 90s…").

### F1.5 Entity richness  [ID: ENTITY]
- Heavily cited text: **20.6%** entity density vs ~5–8% for normal English
  (Brown Corpus / Penn Treebank baselines).
- Loser: "There are many good tools for this task." (0%)
  Winner: "Top tools include Salesforce, HubSpot, and Pipedrive." (~30%)
- Name specific brands, tools, people, standards, places — including
  competitors. Entities lower answer perplexity and are verifiable.

### F1.6 Balanced sentiment ("analyst voice")  [ID: SUBJ]
- Cited text averages subjectivity **0.47** (0 = pure fact, 1 = pure opinion).
- Avoid both dry fact-listing (~0.1) and hype (~0.9). Pair a fact with what it
  means: "While the iPhone 15 uses a standard A16 chip, its low-light
  performance makes it a strong choice for content creators."

### F1.7 Business-grade readability  [ID: READ]
- Cited: Flesch-Kincaid grade **16** (college). Non-cited: **19.1** (PhD).
- Fix long, winding, jargon-stacked sentences → subject-verb-object, short to
  moderate length. Note the study explicitly says this is **not** "dumb it
  down" — winners still use business-grade vocabulary. Target ≈ The
  Economist / HBR, not grade 8.

### Study 1 caveats
- "P-value of 0.0" means vanishingly small, not literally zero; and with 18K
  rows nearly any difference is significant — effect sizes matter more.
- FK grades of 16 vs 19.1 are both high; they were likely measured on the
  cited *chunks*, not whole pages. Use as a direction ("reduce if >18"), not
  a target to hit exactly.
- Entity density definition (which tokens count) isn't fully specified; our
  script uses a heuristic, so compare relative to baselines, not exactly.

---

## Study 2 — Tables in ChatGPT citations vs. Google results (Nectiv)

- **Source:** Chris Long, Nectiv —
  https://nectivdigital.com/blog/new-data-study-chatgpt-citations-are-2-3x-more-likely-to-include-a-table-than-google-search
- **Dataset:** B2B SaaS vertical. Google set ≈ 25K ranking URLs for Capterra's
  top queries (via Ahrefs Keywords Explorer). ChatGPT set = "Top Cited Pages"
  from Nectiv's AI Tracker, running Capterra's query set as prompts (size of
  the cited-URL set not stated in the post).
- **Method:** Screaming Frog custom extraction checking each URL for a
  `<table>` element in the content.

### F2.1 Tables  [ID: TABLE]
| Dataset | Pages with a `<table>` |
|---|---|
| Google ranking pages | **13%** |
| ChatGPT-cited pages | **30%** |
- ChatGPT citations are **2.3x** more likely to contain a table.
- Pattern in top-cited domains: SoftwareConnect (250 citations / 90 days)
  puts a table **at the top of every roundup** with columns for product name,
  key feature and starting price; ChatGPT's answers reuse those rows.
  Cotocus.com (443 citations / 90 days, outranking Forbes, Software Advice
  and Capterra) has bare HTML pages: headings, bullet lists, tables.
- Other examples cited: ClickUp, Nextiva, PeerSpot, TechRadar, Zapier.
- Implication: for comparison, roundup, pricing and "best X" content, add a
  real HTML `<table>` that summarizes the options, near the top. Tables
  rendered as images, or as div/CSS grids, don't count: the study only
  detected `<table>` elements, and those formats are harder for crawlers to
  chunk.

### Study 2 caveats
- Correlational, and the author says so. Tables cluster on comparison
  content, which may be the format ChatGPT likes rather than the table
  itself. Tables are also information-dense, which overlaps with ENTITY.
- The two sets aren't matched URL-for-URL. Google = all ranking pages; ChatGPT
  = the *most*-cited pages. Some of the gap may be "top performers vs. the
  average page" rather than "ChatGPT vs. Google".
- One vertical (B2B SaaS). Don't assume it carries over to, e.g., YMYL or
  local content without other evidence.
- Cotocus shows tables can win even on low-authority, AI-written pages. That
  makes it an argument for structure, not for thin content.

---

## Study 3 — Content freshness & the "stale content penalty" (AirOps)

- **Source:** AirOps, "The Silent Pipeline Killer: How Stale Content Costs You AI
  Citations" (Aug 4, 2025):
  https://airops.com/report/the-impact-of-stale-content-on-ai-visibility. AirOps
  sells AI content-refresh workflows, so it has a commercial interest in
  "freshness matters".
- **Dataset:** 4,000+ pages cited by ChatGPT across 900 high-intent queries
  in 15 industries. Fields: last-updated date, original publish date, query
  intent, industry, content type.
- **Method gap:** the study only examines **cited** pages and describes no
  non-cited control set. How it computed "2x less likely to be cited" isn't
  stated.

### F3.1 Recency of cited pages  [ID: FRESH]
| Last updated | Share of cited pages |
|---|---|
| < 3 months | **35.2%** |
| < 6 months | **53.4%** |
| < 12 months | "over 70%" (headline) |
| > 12 months | 26.2% (but see the 56.4% conflict below) |

### F3.2 Intent changes how fresh content must be  [ID: FRESH-INTENT]
- **Commercial queries:** 60%+ of cited pages updated in the last 6 months;
  **83%** within 12 months; only ~1 in 5 older than a year.
- **Informational queries:** more tolerant. Nearly 1/3 of cited pages were
  over a year old, mostly evergreen how-to and best-practice content.
- **Mixed-intent pages** (cited for both): 50% updated in the last 3
  months, the highest recency rate of any group.

### F3.3 Last-updated date matters more than publish date  [ID: FRESH]
- 26% of pages published more than a year ago were updated in the last 3
  months, so old URLs keep getting cited when they're maintained.
- Claimed: pages not updated in 12+ months are ">2x less likely" to be
  cited, and lose ">50%" of citation likelihood on commercial queries.

### F3.4 Freshness window varies by industry  [ID: FRESH-WINDOW]
| Vertical | Suggested refresh cadence |
|---|---|
| SaaS, Finance, News | **< 3 months** |
| Most commercial content | ≤ 6 months |
| Education, Research, evergreen informational | ~12 months |
| Healthcare & Wellness, Productivity, Travel (informational) | slower, but 30%+ of cited Healthcare content was refreshed in the last 6 months |

### Study 3 caveats
- **Internal inconsistency:** the report says both "26.2% hadn't been updated
  in over a year" and "56.4% of cited pages hadn't been updated in over a
  year". Both can't be true for the same population (the 56.4% may be a
  subset, or measured by publish date). Rely on the < 3 / < 6 month numbers
  and the intent split, which are internally consistent.
- **No baseline:** without the freshness distribution of *non-cited* pages
  (or of the web at large), "70% updated within 12 months" doesn't prove a
  preference. Much of the web's actively maintained content is recent. The
  "2x" and "50%" penalty figures have no shown method, so treat them as
  directional only.
- The industry freshness windows are presented as conclusions without the
  supporting numbers. Use them as cadence guidelines, not thresholds.
- It's unclear how "last updated" was detected (visible date, schema,
  HTTP header). The skill checks all of these.
- Freshness has to be **substantive**. Nothing here supports bumping the
  date without changing content, and LLMs and Google can both compare
  content versions. Never recommend fake date changes.

---

## Study 4 — Content structure & chunking: a controlled retrieval test (Chris Green)

- **Source:** Chris Green, "How Content Structure Matters for AI Search"
  (https://www.chris-green.net/post/content-structure-for-ai-search)
  (Jun 13, 2025; updated Jun 16, 2025). Code and outputs published on Git.
  Feedback from Dawn Anderson and others.
- **Design:** a **controlled experiment**, the only one in this file so far.
  3 articles on distinct topics, each rewritten in 3 styles: (a) dense prose,
  (b) the same prose with headings + lists, (c) Q&A. Each was tested against
  5 mostly top-of-funnel queries.
- **Pipeline:** content split with 4 chunking methods (token-based, recursive
  [LangChain], HTML-aware [h1–h4, p, li, div], semantic [embedding
  breakpoints, 95th pct]). Chunks of ~100 tokens with 20-token overlap,
  embedded with Google Vertex `text-embedding-005`, indexed with HNSW. The
  score is the cosine similarity of the best-matching chunk per query.
- **What it measures:** **retrieval-stage semantic match only**, not
  citations or rankings.

### F4.1 Format vs. retrieval match  [ID: CHUNK]
| Format | Query-to-best-chunk similarity |
|---|---|
| Q&A | **Highest in every scenario** (every chunker, every query type) |
| Structured (headings + lists) | **Close to Q&A for non-question queries** |
| Dense prose | **Lowest in every test** |
- Takeaway: Q&A is the best default when the goal is matching queries. But
  well-structured content with proper HTML headings and lists gets most of
  the benefit, so Q&A doesn't have to be forced onto every page.
- Mechanism: retrieval scores chunks, not pages. If the key facts for a
  query sit in one self-contained chunk (~100 tokens ≈ 75 words), that chunk
  scores high. If they're spread across chunks, relevance gets diluted.

### Practical rules derived (for the skill)
- Break up dense prose with real HTML subheadings and lists. Huge
  paragraphs (>120 words) and long sections with no subheadings (>300
  words) span several chunks.
- Make each section **self-contained**. Open a section by naming its subject
  rather than with a pronoun that points back to an earlier chunk ("It
  helps…", "This means…"). Once the text is chunked, "It" has nothing to
  refer to. This is the retrieval-side reason behind Study 1's "entity
  echoing".
- Keep a question's answer and its key supporting facts within ~75 words
  of the heading that asks it.

### Study 4 caveats
- **Tiny sample** (3 articles × 3 styles × 5 queries). The author calls it
  illustrative, not definitive.
- Measures embedding similarity, which is one retrieval stage. Reranking,
  authority, freshness and other signals come after it.
- Uses a **Google** embedding model. ChatGPT's retrieval stack (Bing index +
  OpenAI models) may behave differently, though the direction matches Study
  1's ChatGPT citation data.
- The content variants had to be rewritten by hand, so differences in
  writing quality between variants may affect the results.

---

## House rules (Nectiv), built on the studies above

### H1 Key Takeaways section  [ID: TAKEAWAYS]
- **Rule:** every article has a section headed "Key Takeaways" with **3–6
  bullets**, placed as the **first thing on the page**: directly under the
  H1 title, above the introduction.
- **Evidence:** Study 1 [POS-DOC]: 44.2% of ChatGPT citations come from the
  first 30% of a page, against 31.1% from the middle and 24.7% from the end.
  Putting the takeaways first places every bullet at the very start of that
  zone, ahead of any intro copy. Bullets also follow Study 4
  [CHUNK]: each one is a short, self-contained, quotable chunk.
- **Not from a study:** the 3–6 count, the exact heading and the top-of-page
  placement are Nectiv conventions. Present them as house rules, not measured findings.
- Each bullet is a complete, definitive claim with the page's own entities
  and numbers, never a teaser ("Learn why X matters").
- If a prose summary already sits at the top ("In Brief", "TL;DR",
  "Summary"), convert it into the Key Takeaways list rather than adding a
  duplicate.

---

## Conflicts & open questions
- No direct conflicts yet. Overlap: Study 1 (POS-DOC) and Study 2's top
  examples (SoftwareConnect) both point to **summary material at the top of
  the page**. A comparison table up top serves both factors.
- Study 3 has an internal contradiction (26.2% vs 56.4% stale), noted in its
  caveats. Weigh its intent-split findings above its headline penalty numbers.
- **Studies 1 and 4 agree on Q&A** through independent methods: ChatGPT
  citation correlation (2x more question marks, 78% from headings) and a
  controlled embedding test (Q&A best in every scenario). This is the
  best-corroborated finding in the file, so treat QA as high confidence.
- Apparent tension, resolved: Study 1 says citations mostly come from
  *mid-paragraph* sentences (don't force answer-first sentences), while
  Study 4 says keep answers *in the same chunk* as the question. Both hold.
  The answer has to be in the first ~75 words under the heading, but it
  doesn't have to be literally the first sentence.
- Study 3 pairs naturally with Study 2: the SaaS/commercial pages most likely
  to need tables (roundups, pricing) are also the ones with the shortest
  freshness window (< 3 months). Stale pricing in a table is doubly risky.

## Factor priority (current — effect size × strength of evidence)
1. POS-DOC — front-load key insight (44% of citations, 2.5x vs middle)
2. ENTITY — entity density (20.6% cited vs 5–8% baseline, ≈3x: the
   largest effect in the file). Weighted up as a Nectiv choice: most pages
   miss it badly and it's fixable sentence by sentence. Targets (heuristic):
   ≥12% overall, ≥15% in the intro and Key Takeaways, ≤25% of sentences
   with no entity.
3. TAKEAWAYS — Key Takeaways section with 3–6 bullets, first on the page
   (house rule built on the 44.2% POS-DOC finding; applies to every page).
4. QA + CHUNK — question headings with direct, entity-echoing answers (2x;
   the only finding backed by both citation data and a controlled test).
   Where Q&A doesn't fit, use structured sections (headings + lists)
   instead of dense prose, and make each section self-contained (no
   pronoun-led openers, answer within ~75 words of its heading).
5. TABLE — for comparison/roundup/pricing/"best X" pages only: HTML table
   near the top (2.3x). Lower priority on informational/how-to pages, where
   the study has no evidence.
6. FRESH — commercial pages and SaaS/finance/news: substantive update
   within 3–6 months, with an accurate visible + schema dateModified.
   Informational/evergreen: ≤ 12 months. (Directional only: vendor study,
   no control set; see Study 3 caveats.)
7. DEFINITIVE — definitive statements (1.8x)
8. READ — reduce over-complex sentences (FK 19 → 16)
9. SUBJ — analyst voice (~0.47)
10. POS-DOC (end) — add a summary/conclusion section before the footer

Raise a factor's priority for a specific page when that page misses it
badly. A 2-year-old SaaS pricing page should lead with FRESH whatever its
rank is here.
