# Keyword Validation Strategy (Phase 4)

For every prompt in the library, find a supporting SEO keyword with search volume > 0. This validates that real search demand exists behind the prompt topic, which means LLMs are likely training on content about it.

---

## Core principle: topical, not textual

The supporting keyword does NOT need to match the prompt text exactly. The relationship is topical, not textual.

Examples:

- Prompt: "What are the best ways to start a retail business?" → Keyword: "how to start a retail business" (320 vol)
- Prompt: "How do net 30 payment terms work in wholesale?" → Keyword: "net 30" (9,400 vol)
- Prompt: "What is Salesforce and how does it work?" → Keyword: "salesforce crm" (~135,000 vol)

## Prefer higher-volume keywords when equally relevant

If an exact-match keyword has 50 volume but a closely-related keyword has 5,000 volume, use the higher-volume one. The goal is showing the topic has demand, not finding a perfect textual match.

## Cast a wide net

Do not limit keyword research to the most obvious seed terms. Look for high-volume keywords in adjacent topic areas that still validate the prompt's relevance. For example, a skincare brand's prompts about face cleansers could map to "face wash" (135K volume) rather than just "best face cleanser for my skin type" (300 volume). A SaaS brand's compliance prompts might map to "GDPR compliance" (9.9K) rather than a niche product-specific keyword.

Run `expand_topic_keywords.py` across diverse seed keywords — category terms, competitor terms, adjacent topic terms — to find the strongest keyword anchors.

---

## Source priority

When picking the `supporting_keyword` for each prompt, work through sources in this order:

### 1. Keyword CSVs the user uploaded (use first)

If the user shared any keyword research / SEO-audit CSVs in Phase 1a, consolidate them:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/scan_existing_keywords.py --paths <file_or_dir>... --out geo_tracking/output/existing-keywords.csv
```

`--paths` accepts file paths (individual CSVs) or directory paths (recursively scanned). The script auto-detects CSVs that have a `keyword` column and a `search_volume`-style column (also accepts `volume`, `monthly searches`, `sv`, etc.), dedupes by lowercase keyword (keeping the highest volume), and sorts by volume desc.

These keywords have already been vetted by the user — they reflect real research, real client context, or real competitive intelligence. Use them first.

If the user shared no keyword data, skip this step.

### 2. DataForSEO topic expansion (fill the gaps)

For prompts where no existing keyword fits, expand the keyword universe across category and competitor terms:

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/expand_topic_keywords.py --seeds "category-term-1" "category-term-2" "competitor-term" --limit-per-seed 30 --out geo_tracking/output/expansion.csv
```

Run this multiple times with different seed sets if needed — one run for category terms, another for competitor terms, another for adjacent-topic terms.

### 3. Ad hoc API lookups (only for stragglers)

For the last 5-10 prompts where neither existing nor expansion data fits, write or modify the supporting_keyword by hand and rely on `validate_prompt_keywords.py` to look up the volume. The script's `candidate_keywords` column will surface alternatives for any keyword that comes back not_found or zero_volume.

---

## Cut or revise prompts with no demand

If a prompt topic has zero meaningful search volume from any source, either:

- **Revise** the prompt to a nearby topic that does have volume (e.g., narrow → broader, or shift the framing).
- **Cut** the prompt entirely if revision is not natural.

Every final row must have `search_volume > 0`. The Phase 5 verifier enforces this as a hard-fail check.

---

## Script selection cheat sheet

| Phase 4 step                                         | Tool                              |
|------------------------------------------------------|-----------------------------------|
| Consolidate keyword CSVs the user uploaded           | `scan_existing_keywords.py`       |
| Bulk-discover related keywords from category seeds   | `expand_topic_keywords.py`        |
| Look up volume for each prompt's chosen keyword      | `validate_prompt_keywords.py`     |
| Find what the brand domain itself ranks for          | `discover_brand_keywords.py` (Phase 1) |

Each script preflights credentials and exits 5 with setup instructions if anything is missing. All output CSVs use stdlib `csv` with QUOTE_MINIMAL, safe for keywords/prompts containing commas or quotes.

---

## How `validate_prompt_keywords.py` decides

Pass-by-pass logic for each prompt row's `supporting_keyword`:

1. If empty → `status = blank`. Move on.
2. **Pass 1** (if `--existing` provided): case-insensitive exact match against the consolidated uploaded-keywords CSV.
   - Found → `status = from_existing`. Skip the API call.
3. **Pass 2** (API): `keyword_suggestions(keyword, limit=5)`.
   - Exact lowercased match with volume > 0 → `status = ok`.
   - Exact match with volume == 0 → `status = zero_volume` and `candidate_keywords` populated.
   - No exact match → `status = not_found` and `candidate_keywords` populated.

The script **never** overwrites `supporting_keyword`. When status is `not_found` or `zero_volume`, the `candidate_keywords` column gives the agent up to 5 alternatives to choose from on the next iteration (format: `"kw1 (vol1); kw2 (vol2); ..."`).

After a Step-4 run, the agent revises any non-`ok`/`from_existing` rows (Phase 4 Step 5 is mandatory) and re-runs the script until every row has volume > 0.
