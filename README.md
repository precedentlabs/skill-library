# skill-library

Agent skills from Precedent Labs, packaged as a Claude Code plugin marketplace.

## Use as a marketplace

```
/plugin marketplace add precedentlabs/skill-library
/plugin install review-loop@precedentlabs-skills
/plugin install optimization@precedentlabs-skills
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
| review-loop | `review-fix-fanout` | After a parallel review: triage findings, fan fixes out to model-tiered subagents with one owner per file, one verification gate |
| review-loop | `implement-review-fix-loop` | Implement in disjoint units, then review → fix rounds per unit until no critical/major/minor finding is left: severity scale, convergence rule, diff-scoped reviews, backlog, worktrees, final gate and smoke test (prompt templates included) |
| review-loop | `triage-findings` | Findings in (review report, backlog, scanner output), decisions out: verify, apply explicit gates and value-versus-cost criteria, then fix now / sweep / defer / reject / needs decision. Invoke with the source: `/review-loop:triage-findings backlog.md` |
| optimization | `optimize` | Metric-driven loop: frame the goal, build a baseline and noise floor, profile, one change per iteration, accept or reject by measurement, equivalence gate, record, stop rules. Invoke with the goal: `/optimization:optimize cut cold-start time` |

## Adding a skill

1. Put it at `plugins/<plugin>/skills/<name>/SKILL.md` with `name` and `description`
   frontmatter (description starts with "Use when…").
2. New plugin: add its `plugin.json` and an entry in `marketplace.json`.
3. Bump the plugin `version` in both files when a skill changes.
