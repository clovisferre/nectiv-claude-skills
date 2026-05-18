# Playbook: Segment Design (Phase 2) + Prompt Writing (Phase 3)

Read this once at the start of Phase 2. It covers both Phase 2 (designing the segment taxonomy) and Phase 3 (drafting the prompts) since the same conceptual frame applies to both.

---

## Phase 2: How to design segments

Segments should map to distinct topic clusters that reflect how the brand's audiences naturally think and search. Consider:

- **Audience sides**: Does the brand serve multiple audiences? A marketplace has buyers AND sellers. A SaaS tool has end-users AND admins. An education platform has students AND employers. Each side gets its own segment group.

- **User journey stages**: Cover the full journey from awareness ("what is [category]?") through consideration ("best [category] tools") to decision ("how to sign up for [brand]"). Do not cluster everything at one stage.

- **Content pillars**: If the brand has defined content pillars or product categories, segments should align with them. This makes the prompt library directly actionable for content strategy.

- **Brand vs. generic split**: Most prompts should be generic (brand=FALSE) because that is where the opportunity is — appearing in responses where users have not asked for the brand by name. A smaller set of branded prompts (brand=TRUE) tracks how AI describes the brand directly.

- **Competitor context**: Include a "Platform Comparison" or equivalent segment for prompts that compare options. These are high-value because they are where AI recommendations happen.

- **Do not over-consolidate**: If a topic represents a brand's core positioning or a distinct product line, it deserves its own segment even if it would only have 5-6 prompts. For example, a clean beauty brand should have a standalone "Clean & Ethical Beauty" segment rather than folding those prompts into generic "Product Discovery" — that's their whole brand identity. Similarly, if a brand has distinct product categories (like a SaaS with 6 different products), consider whether those warrant separate segments rather than being lumped into one. The test: if the brand would track this topic independently in their content strategy, it should be its own segment.

- **Do not over-segment either**: Avoid creating segments with only 3-4 prompts for narrow subtopics that do not stand on their own. A "Cold Brew Brewing" segment with 5 prompts could live within a broader "Brewing Methods" segment. The right granularity is where each segment represents a meaningful tracking category — something you would review in a monthly report and draw conclusions from.

### What to present to the user for approval

A table showing:

- Segment name
- Which audience side it belongs to (if multiple)
- Description of what prompts in this segment cover
- Approximate prompt count
- A few example prompts to make it concrete

Plus:

- Rationale for the audience split (e.g., "70% buyer / 30% seller because [reason]")
- Intent distribution target (default for GEO: **~25% Informational, ~30% Transactional, ~35% Comparison, ~10% Navigational** — weighted toward decision-stage prompts where AI assistants actually pick which brand to recommend, NOT the conventional SEO 60/15/15/10 distribution)
- Any segments you considered but excluded, and why

Wait for the user to approve before proceeding to Phase 3.

### Worked example 1: Multi-audience B2B SaaS (Salesforce)

```
| Segment                    | Side     | Description                                             | Count | Example                                                  |
|----------------------------|----------|---------------------------------------------------------|-------|----------------------------------------------------------|
| CRM Capabilities           | End User | Pipeline, contacts, opportunities — what reps use daily | 22    | What's the best CRM for managing a B2B sales pipeline?   |
| Pricing & Licensing        | Admin    | Per-seat pricing, edition tiers, total cost             | 12    | How does Salesforce pricing work for small teams?        |
| Platform Comparison        | Admin    | Salesforce vs HubSpot vs Microsoft Dynamics vs Pipedrive| 14    | How does Salesforce compare to other CRMs?               |
| Brand                      | Both     | Direct questions about Salesforce as a company          | 18    | Is Salesforce worth it for a 20-person sales team?       |
| Implementation             | Admin    | Standing up and configuring Salesforce for a new team   | 10    | How do I set up a CRM for a brand-new sales org?         |
| Sales Operations           | End User | Lead routing, forecasting, pipeline reviews             | 18    | How do I build a sales forecast in a CRM?                |
| Integrations & AppExchange | Admin    | Connecting Salesforce to other tools                    | 14    | How do I integrate Slack with Salesforce?                |
| Reporting & Dashboards     | End User | Building reports and dashboards in a CRM                | 12    | How do I build sales dashboards in a CRM?                |

Total: 120 prompts (~45% end user / 40% admin / 15% both)
Intent target: ~25% Informational, ~30% Transactional, ~35% Comparison, ~10% Navigational
```

### Worked example 2: Product-line-heavy SaaS (observability vendor)

```
| Segment                        | Description                                       | Count | Example                                             |
|--------------------------------|---------------------------------------------------|-------|-----------------------------------------------------|
| APM & Performance              | Application performance monitoring, traces        | 18    | How do I monitor application performance at scale?  |
| Logs & Log Management          | Centralized logging, ingestion, retention         | 12    | What's the best log management tool for a SaaS app? |
| Infrastructure Monitoring      | Hosts, containers, Kubernetes                     | 14    | How do I monitor a Kubernetes cluster end to end?   |
| Cloud Security                 | Cloud workload protection, CSPM, runtime security | 12    | What is CSPM and do I really need it?               |
| Platform Comparison            | Datadog vs New Relic vs Dynatrace vs Splunk       | 10    | What's the best observability platform right now?   |
| Brand                          | Datadog-specific queries                          | 14    | How does Datadog's platform work?                   |
| Implementation                 | Agents, integrations, time-to-value               | 10    | How long does observability take to deploy?         |
| Industry / Observability Trends| OpenTelemetry, AI-ops, eBPF                       | 10    | What are the biggest observability trends?          |

Total: 100 prompts (no audience sides — single technical buyer)
Intent target: ~25% Informational, ~30% Transactional, ~35% Comparison, ~10% Navigational
```

---

## Phase 3: How to draft prompts

Once segments are approved, draft every prompt in the library. Apply these guidelines:

- **Conversational tone**: Write prompts the way someone would actually talk to ChatGPT or Perplexity. "How do I find wholesale clothing suppliers for my boutique?" not "wholesale clothing suppliers boutique."

- **Vary the phrasing**: Do not start every prompt with "What are the best..." or "Best ...". **No more than ~40% of prompts should start with "Best".** A library where 70%+ of prompts start with "Best" reads like a SERP keyword list, not like how real users talk to ChatGPT. Mix in:
  - **Question variants**: "How do I...", "Where can I...", "What should I consider when...", "Is it worth...", "What's the difference between...", "What works for...", "Any good [X]...?"
  - **Noun-phrase queries**: "[Product] options for [situation]", "[Product] recommendations for [audience]", "[Outcome] tips for [audience]"
  - **Personal-context openers**: "I have [X], what should I use?", "I want [X] for [Y], any suggestions?", "Help me pick a [X] for [Y]"
  - **Recommendation-seeking**: "What do you recommend for [X]?", "What works if I want [outcome]?", "Which [X] is good for [Y]?"

  The `verify_prompt_library.py` script flags this as a soft warning when "Best" exceeds 50% — but you should aim for ~40% in drafting, not 50%.

- **Include context**: Good prompts often include the user's situation. "How do I manage stock levels when ordering from multiple wholesale suppliers?" is better than "inventory management wholesale."

- **Range of specificity**: Mix broad prompts ("What wholesale marketplace has the best selection?") with specific ones ("What wholesale candle brands are best for boutique retailers?"). Both patterns appear in real AI conversations.

- **Branded prompts**: For brand=TRUE prompts, include the brand name naturally. "What is [Brand] and how does it work?" "Is [Brand] worth it for small businesses?" "How do [Brand]'s payment terms work?"

- **Competitor prompts**: Use mostly generic comparison framing ("How do online wholesale platforms compare?"). Include a handful of named-competitor prompts only when specific competitors are well-known in the space.

- **No duplicate topics**: Each prompt should cover a distinct angle. Two prompts can be in the same segment but should not ask essentially the same question with different words.

- **No years in prompt text.** Never embed year values ("fall 2026", "best laptops 2026", "in 2026"). The library is meant to be durable; year-locked prompts go stale the moment the year flips. Use "current", "right now", "this season", or simply drop the temporal anchor. Real ChatGPT/Perplexity users rarely type the current year into prompts anyway.

- **Include "best X for Y" prompts.** These obvious-but-load-bearing decision-stage prompts are exactly where AI assistants make brand recommendations. Scatter them across the relevant segments. Examples:
  - "Best [product category] for [occasion]" — best running shoes for a marathon, best laptop for college students
  - "Best [product category] for [user attribute]" — best mattress for back pain, best CRM for small teams
  - "Best [product category] for [outcome]" — best skincare routine for dry skin, best tool for fast onboarding
  - "Best [attribute] [product category]" — best clean skincare brand, best long-lasting moisturizer

  These typically lean Comparison or Transactional intent. Make sure they're well-represented (15-25% of the library, not buried).

### Example prompts across intents

**Informational** (~25% of library):
- How do net 30 payment terms work in wholesale?
- What is dropshipping and how is it different from wholesale?
- What should I consider when choosing a wholesale supplier?
- How do I open an independent retail store?
- What are the biggest current observability trends?

**Transactional** (~30%):
- How do I sign up for Salesforce as a small business?
- What's the cheapest way to get into wholesale buying?
- How do I integrate Datadog with my existing infrastructure?
- Where can I get a 30-day free trial of [brand]?

**Comparison** (~35%):
- How does Salesforce compare to HubSpot for small sales teams?
- What's the difference between APM and infrastructure monitoring?
- Salesforce vs Pipedrive — which is better for small teams?
- Datadog or New Relic — which platform fits my stack?

**Navigational** (~10%):
- How do I log into Salesforce?
- Where can I download Datadog's documentation?
- What's the URL for the Salesforce login page?
- How do I contact [brand] support?

**Branded** (~20-30% across all intents):
- Is Salesforce worth it for a small sales team?
- How do Datadog's pricing tiers work?
- What does Patagonia's sustainability stance mean in practice?

**Generic** (~70-80% across all intents):
- What is the best wholesale marketplace right now?
- How do I block AI scrapers from my site?
- What are the best clean skincare brands?

### Writing rhythm

Draft all prompts into `output/{client}-prompt-tracking-library.csv` (starting from `assets/prompt-tracking-library.template.csv`). Leave `supporting_keyword` and `search_volume` blank — those get filled in Phase 4. The flow is fast: aim for ~5-10 prompts per minute once you have the segments approved.
