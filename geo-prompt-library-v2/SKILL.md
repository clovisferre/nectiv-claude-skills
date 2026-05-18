---
name: geo-prompt-library-v2
description: Build a GEO (Generative Engine Optimization) prompt tracking library for any brand. Creates a structured CSV of natural-language prompts that LLM users would ask, organized by segments, validated with SEO keyword data to prove real search demand exists behind each prompt. Auto-invoke when the user mentions building a prompt library, GEO tracking, AEO prompts, AI visibility monitoring, prompt tracking for a brand, generative engine optimization, or wants to create prompts to track how a brand appears in AI-generated responses. Also trigger when user mentions tracking ChatGPT, Perplexity, or AI Mode visibility for a brand, even if they don't say "GEO" or "prompt library" explicitly.
---

# GEO Prompt Tracking Library Builder

Build a library of natural-language prompts that real users would ask AI assistants (ChatGPT, Perplexity, Google AI Mode), organized by audience segments, and validated with SEO keyword data. The output CSV feeds into daily AI visibility monitoring.

Good prompts are conversational (how a real person talks to an AI, not how they type into Google), cover the full user journey, and map to topics with proven search demand. The SEO keyword validation is not about matching prompts to keywords 1:1; it is about proving that the topic behind each prompt reflects something people actually search for, which means LLMs are likely training on and generating content about it.

## Prerequisites

This skill calls the DataForSEO API. Before first use, run from your workspace root:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/check_setup.py
```

If it reports missing credentials, follow `references/setup.md`. Requires Python 3.9+ (stdlib only, no `pip install` needed).

**Script invocation convention:** all script commands in this skill are written to be run **from the workspace root** (the directory that contains `.claude/`). Do not `cd` into the skill folder; the script paths assume your current directory contains `.claude/skills/geo-prompt-library-v2/`.

## Input

The user provides at minimum a **brand name**. They may also provide:

- A brand domain (e.g., `salesforce.com`)
- Target prompt count (default: ~100-130)
- Specific audience sides or segments to focus on
- Custom CSV columns beyond the default 6
- Any helpful documents to share upfront (see Phase 1a)

## Output

A CSV file saved to `geo_tracking/output/{brand-slug}-prompt-tracking-library.csv` (relative to the current working directory). All script paths in this skill default to this convention; pass `--out` explicitly if you want a different location.

Default columns:

```
text,segments,intent,brand,supporting_keyword,search_volume
```

- **text**: Natural-language prompt. Conversational, the way someone would actually talk to ChatGPT. Not keyword-style.
- **segments**: Category bucket the prompt belongs to (e.g., "Product Sourcing", "Platform Comparison").
- **intent**: One of: Informational, Transactional, Comparison, Navigational.
- **brand**: TRUE if the prompt text contains the brand name, FALSE otherwise.
- **supporting_keyword**: A related SEO keyword that validates real search demand exists behind this prompt topic. Does not need to be an exact match to the prompt text.
- **search_volume**: Monthly search volume for the supporting keyword.

The Phase 4 validator adds two more columns during processing: `status` and `candidate_keywords`. The final file is the version the agent has revised so every row has `search_volume > 0`.

---

## Workflow

### Phase 1: Brand context loading

**1a. Ask for documents first (REQUIRED before web research)**

Before doing any web research, ask the user to share any documents that would help shape the prompt library. The richer the context here, the better the segments and prompts will be.

Examples of what to ask for:

- Brand strategy decks, positioning docs, or messaging guides
- Content pillars or editorial plans
- Prior keyword research / SEO audits (CSV files with keyword + search-volume columns are especially valuable — they'll feed Phase 4 directly)
- Competitor analyses or battle cards
- Customer/buyer research, ICP definitions, persona docs
- Past onboarding notes, brand interviews, or meeting transcripts

Tell the user they can drag files into the Claude Code chat, attach them via their IDE, or paste content directly. If they say they have nothing to share, that's fine — proceed to 1c.

**1b. Read and synthesize what was shared**

For each file the user provided:

- Read it (Read tool, or whatever file-reading tool is available in the session)
- Capture: brand positioning, audiences, content pillars, named competitors, product/service taxonomy, any voice/tone constraints
- Note any keyword CSVs separately — you'll consolidate them with `scan_existing_keywords.py` in Phase 4 Step 1

Take 1-3 sentences to summarize back to the user what you took from each doc, so they can correct misreadings before you commit to a segment plan.

**1c. Web research**

Discover what keywords the brand domain ranks for:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/discover_brand_keywords.py \
    --url <brand_domain> \
    --out geo_tracking/output/brand-ranked-keywords.csv
```

If the script reports 0 results, it will hint at loosening filters (`--max-position 30 --min-volume 1`). Re-run with those if the brand is small.

If a web fetch tool is available, ALSO fetch the brand's homepage and key product pages for additional context. Otherwise rely on `discover_brand_keywords.py` plus general web knowledge.

**1d. Set up the output directory**

If `geo_tracking/` does not exist in the current working directory, create it and copy the asset template into place:

```bash
mkdir -p geo_tracking/output
cp .claude/skills/geo-prompt-library-v2/assets/geo_tracking_CLAUDE.template.md \
   geo_tracking/CLAUDE.md
```

The placeholders inside that CLAUDE.md get filled in Phase 5.

### Phase 2: Segment design & planning

This is the most important creative step. **Read `references/playbook.md`** before designing segments.

Present a segment plan to the user INLINE as a table:

| Segment name | Audience side | Description | Approx count | Example prompts |

Plus rationale for the audience split (if multiple sides), intent distribution target (**default for GEO: ~25/30/35/10 for Informational/Transactional/Comparison/Navigational** — weighted toward decision-stage prompts where AI assistants pick brands, NOT the conventional SEO 60/15/15/10), and any segments considered but excluded.

**WAIT for user approval** before drafting any prompts. They may want to adjust counts, add/remove segments, or shift the audience balance.

### Phase 3: Prompt drafting

`references/playbook.md` (already read in Phase 2) also covers prompt-writing guidelines and a worked example bank.

Start the prompts CSV from the template:

```bash
cp .claude/skills/geo-prompt-library-v2/assets/prompt-tracking-library.template.csv \
   geo_tracking/output/<brand-slug>-prompt-tracking-library.csv
```

Append rows. Leave `supporting_keyword` and `search_volume` blank for now (Phase 4 fills them).

### Phase 4: SEO keyword validation

**Read `references/keyword-validation.md`** for the strategy (topical-not-textual, source priority, when to use which script).

**Step 1**: consolidate any keyword data the user uploaded in Phase 1a (skip if they had none).

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/scan_existing_keywords.py \
    --paths <file_or_dir>... \
    --out geo_tracking/output/existing-keywords.csv
```

`--paths` accepts one or more file paths (individual CSVs) or directory paths (which get recursively scanned for CSVs). The script extracts rows with `keyword` + `search_volume` columns (with flexible header matching), dedupes by lowercase keyword (keeping the highest volume), and sorts by volume desc. If the user shared no keyword data, skip this step and skip the `--existing` flag in Step 4.

**Step 2**: bulk-discover related keywords for thin-coverage segments.

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/expand_topic_keywords.py \
    --seeds "category-term-1" "competitor-term" "adjacent-topic" \
    --limit-per-seed 30 \
    --out geo_tracking/output/expansion.csv
```

Run multiple times with different seed sets if needed (one run per topic cluster).

**Step 3**: fill `supporting_keyword` for each prompt. Procedure:

1. Open `existing-keywords.csv` (already sorted by volume desc) and `expansion.csv`.
2. For each prompt with a blank `supporting_keyword`:
   - Scan existing-keywords.csv top-down. Pick the highest-volume keyword whose topic relates to the prompt (even loosely; remember: topical, not textual).
   - If nothing in existing fits, scan expansion.csv the same way.
   - If neither has anything topical, write a plausible keyword by hand. Step 4 will flag it if it doesn't exist.
3. Save the prompts CSV.

The relationship is **topical, not textual** — "What are the best ways to start a retail business?" can map to the higher-volume `how to start a retail business`, not the exact textual match.

**Step 4**: validate volumes.

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/validate_prompt_keywords.py \
    --prompts geo_tracking/output/<brand-slug>-prompt-tracking-library.csv \
    --existing geo_tracking/output/existing-keywords.csv \
    --out geo_tracking/output/<brand-slug>-prompt-tracking-library.csv
```

(Omit `--existing` if Step 1 was skipped.)

This writes `search_volume` and `status` for every row. For any row that is `not_found` or `zero_volume`, it also emits a `candidate_keywords` column with up to 5 alternatives from the API. Rows already validated on a prior run (status `ok`/`from_existing` with volume > 0) are **skipped** by default to save API calls; pass `--force` to re-validate everything.

**Step 5** (REQUIRED): revise every row with `status` in {`zero_volume`, `not_found`, `blank`}. Use the `candidate_keywords` column as a starting point. **When you change a row's `supporting_keyword`, also clear its `status` cell** so it gets re-validated on the next run (otherwise the cache treats it as already-valid). Re-run Step 4 after changes. Every final row must have `search_volume > 0` (Phase 5 verifier enforces this as a hard fail).

### Phase 5: Output & verification

Run the verifier:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/verify_prompt_library.py \
    --csv geo_tracking/output/<brand-slug>-prompt-tracking-library.csv \
    --brand "<BrandName>" \
    --target-count <n>
```

The markdown report shows pass/fail per check plus distributions (segments, intent, branded-vs-generic, top keywords by volume).

Address any **hard failures** (exit 1) before proceeding. Soft warnings (intent drift, duplicates, target-count deviation) are informational; address them only if they reflect real issues.

Fill the `{{placeholders}}` in `geo_tracking/CLAUDE.md` per the `> [GUIDANCE — REMOVE BEFORE SAVING]` blockquotes already in the template. **Strip every guidance blockquote** before saving — the final file should contain zero `> [GUIDANCE` markers.

Re-run the verifier with `--claude-md` to confirm:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/verify_prompt_library.py \
    --csv geo_tracking/output/<brand-slug>-prompt-tracking-library.csv \
    --brand "<BrandName>" \
    --claude-md geo_tracking/CLAUDE.md
```

Exit 0 means everything passes.

Present the user a summary INLINE:

- Total prompts by segment
- Branded vs generic split
- Intent distribution
- Top keywords by volume
- Any prompts that were cut or revised during validation, and why

---

## Gotchas

Things that defy reasonable assumptions and will trip the agent up unless warned:

- **`discover_brand_keywords.py` returns 0 for smaller brands by default.** Default filters require top-10 organic ranking AND volume ≥ 10. Brands that don't rank in the top 10 (most small/mid-size brands) get an empty CSV. The script will print a HINT suggesting `--max-position 30 --min-volume 1` — follow it.

- **`scan_existing_keywords.py` silently produces an empty CSV** when none of the supplied paths contain CSVs with `keyword`+`search_volume` columns. The stderr summary will say `0 unique keywords across 0 source file(s)`. If you see this, skip the `--existing` flag on the Step 4 validator call; passing an empty existing-keywords.csv produces the same end result but wastes a file read.

- **DataForSEO indexes phrasing literally.** "time tracking" alone may return `not_found` even though `time tracking software` (18,100 vol) is valid; "asana time tracking" may not exist but `time tracking asana` does. This is normal — the `candidate_keywords` mechanism in Phase 4 Step 5 surfaces the indexed variants. Don't treat a `not_found` as "this topic has no demand"; treat it as "rephrase to a variant DataForSEO indexes."

- **`validate_prompt_keywords.py` caches by default.** Rows with status `ok` or `from_existing` and `search_volume > 0` are skipped on re-runs. If you change a row's `supporting_keyword` during Phase 4 Step 5, also clear that row's `status` cell so the cache misses and re-validates. Or pass `--force` to invalidate the whole cache.

- **`verify_prompt_library.py` brand check is case-insensitive substring, not word-bounded.** Short brand names that appear inside other words can false-positive (e.g., `--brand AI` would flag "fairly", "stairway", etc.). Use the full brand name as it appears in prompts to minimize this.

- **`keyword_suggestions` returns nothing for nonsense or extremely niche keywords.** When the agent invents a supporting_keyword that doesn't actually exist in DataForSEO's index, status will be `not_found` with an empty `candidate_keywords`. Treat as a signal to either rephrase or pick a known parent topic.

- **Navigational intent target (~10%) is hard to hit for SaaS verticals.** Navigational prompts are almost entirely brand-specific ("where do I sign up for X", "how do I log into X"), which caps how many distinct ones you can write. If the final split is 5-8% Navigational, that's usually fine — the soft warning is informational, not a hard fail.

## References

Load these when the workflow above tells you to:

- `references/setup.md` — first-time DataForSEO setup (env vars or `.env`)
- `references/playbook.md` — Phase 2 segment design + Phase 3 prompt writing
- `references/keyword-validation.md` — Phase 4 strategy and script-selection guide

## Scripts

All under `scripts/`. Each script supports `--help`. Exit codes: 0 success, 1 generic, 2 invalid args, 3 input not found, 4 API/network, 5 setup incomplete.

- `check_setup.py` — verify DataForSEO credentials (1 API row per run)
- `scan_existing_keywords.py` — consolidate user-supplied keyword CSVs (no API)
- `discover_brand_keywords.py` — brand domain ranked-keywords lookup
- `expand_topic_keywords.py` — batched keyword-suggestions across seeds
- `validate_prompt_keywords.py` — annotate prompts CSV with volumes + candidates
- `verify_prompt_library.py` — Phase 5 checklist + distribution report (no API)

## Assets

- `assets/prompt-tracking-library.template.csv` — RFC-4180 header row
- `assets/geo_tracking_CLAUDE.template.md` — output document template with `{{placeholders}}` and visible guidance blockquotes
