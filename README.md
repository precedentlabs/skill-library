# skill-library

Agent skills from Precedent Labs, packaged as a Claude Code plugin marketplace.

## Use as a marketplace

```
/plugin marketplace add precedentlabs/skill-library
/plugin install review-fanout@precedentlabs-skills
```

Local checkout works too: `/plugin marketplace add ./skill-library`.

## Layout

```
.claude-plugin/marketplace.json     marketplace catalogue (name: precedentlabs-skills)
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md
```

## Skills

| Plugin | Skill | Use |
|---|---|---|
| review-fanout | `review-fix-fanout` | After a parallel review: triage findings, fan fixes out to model-tiered subagents with one owner per file, one verification gate |

## Adding a skill

1. Put it at `plugins/<plugin>/skills/<name>/SKILL.md` with `name` and `description`
   frontmatter (description starts with "Use when…").
2. New plugin: add its `plugin.json` and an entry in `marketplace.json`.
3. Bump the plugin `version` in both files when a skill changes.
