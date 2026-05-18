# {{brand_name}} GEO Prompt Tracking Library

> [GUIDANCE — REMOVE BEFORE SAVING]
> This is the reference document for {{brand_name}}'s GEO prompt tracking
> library. After filling in every {{placeholder}} below and verifying with
> verify_prompt_library.py --claude-md, REMOVE every `> [GUIDANCE ...]`
> blockquote (this file should contain zero guidance markers when saved).

## Purpose

> [GUIDANCE — REMOVE BEFORE SAVING]
> One paragraph: what this library monitors and why. Mention the assistants
> being tracked (ChatGPT, Perplexity, AI Mode, etc.) and the business goal
> (visibility for branded queries, share-of-voice on category queries, etc.).

{{purpose}}

## CSV format

The library lives at `geo_tracking/output/{{brand_slug}}-prompt-tracking-library.csv` with
columns:

- **text**: Natural-language prompt as a real user would phrase it.
- **segments**: Topic cluster (e.g., "Product Sourcing", "Platform Comparison").
- **intent**: One of Informational, Transactional, Comparison, Navigational.
- **brand**: TRUE if the prompt text contains the brand name; FALSE otherwise.
- **supporting_keyword**: SEO keyword validating real search demand behind the topic.
- **search_volume**: Monthly US search volume for the supporting keyword.

## Segment overview

> [GUIDANCE — REMOVE BEFORE SAVING]
> Markdown table: segment name | prompt count | one-line description.
> Compute prompt count from the CSV's `segments` column (split on `;` if
> any cell contains multiple segments). Order segments by prompt count desc.

{{segment_table}}

## Coverage analysis

### Audience sides

> [GUIDANCE — REMOVE BEFORE SAVING]
> Describe who the brand serves (buyer, seller, end-user, admin, etc.) and
> how prompts split across audiences with percentages. Explain *why* the
> split is what it is — what business rationale drove the allocation.
> Example: "65% end-user / 35% admin because the GEO opportunity is
> capturing user-side feature and how-to prompts; the admin-side is
> smaller because procurement-stage queries already convert via direct traffic."

{{audience_distribution}}

### Intent distribution

> [GUIDANCE — REMOVE BEFORE SAVING]
> Use the soft-warning intent table from verify_prompt_library.py output
> as the source of truth. Default GEO target is ~25% Informational, ~30%
> Transactional, ~35% Comparison, ~10% Navigational (weighted toward
> decision-stage prompts where AI assistants make brand recommendations).
> If the actual split drifts, justify it (e.g., "higher comparison %
> because category is dominated by Platform A vs. Platform B prompts").

{{intent_distribution}}

### Branded vs generic

> [GUIDANCE — REMOVE BEFORE SAVING]
> Count and % from verify_prompt_library.py. Typically generic dominates
> (60-80%) because the opportunity is appearing in non-brand-name queries.
> Branded prompts (20-40%) track how AI describes the brand directly.

{{branded_split}}

## Product/offering mapping

> [GUIDANCE — REMOVE BEFORE SAVING]
> Explicitly list each major product, service, or content pillar and which
> segments cover it. This proves comprehensive coverage and makes gaps
> visible. Example:
> - Core product -> Product Capabilities, Platform Comparison segments
> - Pricing & licensing -> Pricing segment
> - Brand explanation -> Brand segment

{{product_mapping}}

## Competitor references

> [GUIDANCE — REMOVE BEFORE SAVING]
> List the competitors that appear in prompts (or are referenced implicitly
> by category-comparison framing) and why each was chosen. This shows the
> competitive landscape being monitored.

{{competitor_references}}

## Keyword validation summary

> [GUIDANCE — REMOVE BEFORE SAVING]
> Use the top-10-keywords-by-volume from verify_prompt_library.py output
> plus a sentence about coverage strategy (e.g., "Validated against
> high-volume category terms like 'time tracking software' and 'project
> management software' rather than narrow brand-specific terms, to capture
> the broader topic space where AI generates content").

{{keyword_validation_summary}}

## Update triggers

> [GUIDANCE — REMOVE BEFORE SAVING]
> When to rebuild the library and when not to. Suggested template below;
> customize per client.

Rebuild this library when:

- New products, services, or content pillars launch
- New material competitors enter the space
- Quarterly review (volume / intent / segment drift checks)
- Major brand repositioning or messaging shift

Do NOT rebuild for:

- Minor keyword-volume fluctuations (noise, not signal)
- Individual blog posts or one-off content launches
- Short-term campaign-driven topic spikes

## Notes

> [GUIDANCE — REMOVE BEFORE SAVING]
> Any brand-specific tracking conventions, exclusions, or open questions
> the next reviewer should know. If none, delete this section entirely.

{{notes}}
