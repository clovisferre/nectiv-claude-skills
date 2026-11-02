# Nectiv Claude Skills

A collection of open-source [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) built and used by [Nectiv Digital](https://nectivdigital.com). Each skill lives in its own subdirectory and follows the standard Claude Code skill layout (`SKILL.md` + supporting `references/`, `scripts/`, `assets/`).

## Skills

| Skill | What it does |
|-------|--------------|
| [`geo-prompt-library-v2`](./geo-prompt-library-v2) | Build a Generative Engine Optimization (GEO) prompt-tracking library for a brand — segmented natural-language prompts, validated against SEO keyword data via DataForSEO. |
| [`aeo-content-structure-optimizer`](./aeo-content-structure-optimizer) | Audit and rewrite an existing page so ChatGPT and other AI answer engines are more likely to cite it — Key Takeaways, entity density, verified statistics, question headings, tables, chunk structure and freshness, each tied to a published citation study. Delivers a Google Doc with before/after metrics and the full revised article. |

## Installing a skill

Skills live in `.claude/skills/` inside a Claude Code workspace. To use one from this repo, copy the skill's subdirectory into your workspace's `.claude/skills/` folder:

```bash
# From your project root
mkdir -p .claude/skills
cp -R /path/to/nectiv-claude-skills/geo-prompt-library-v2 .claude/skills/
```

Claude Code will pick it up automatically on next launch and auto-invoke it based on the `description` field in `SKILL.md`.

Each skill's `SKILL.md` documents its prerequisites (API keys, environment variables, etc.). Skills may include a `references/setup.md` with first-time configuration steps — check there before first use.

## Contributing

These skills are published as-is — patches and issues welcome via GitHub. We make no guarantees about backward compatibility between versions; skills are versioned in their directory names (e.g. `geo-prompt-library-v2`) when breaking changes ship.

## License

MIT — see [LICENSE](./LICENSE).
