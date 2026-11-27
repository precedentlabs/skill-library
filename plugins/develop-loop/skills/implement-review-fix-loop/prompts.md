# Prompt templates

Replace `<…>`. Keep the severity bar and stop condition in every reviewer prompt. The
role rules (read-only except probes, evidence rule, lenses, ask the orchestrator, output
format, `DESIGN:`, `TIER:` and `VERDICT:` lines) live in the `dl-reviewer` agent; the
architect's in `dl-architect`; implementer, fix and runner tasks are in `tiered-fanout` §4.
The orchestrator runs `git -C <path> add -N .` before sending the round-1 or re-review
prompt, so the diff shows new files. Without plugin agents, paste the agent file's body
above each prompt and set the model as `tiered-fanout` §4 says.

## Architecture map (`dl-architect`, map mode)

```
Mode: map. Feature: <spec / decision-record ids>. Repo rules: <absolute path>.
Redesign signal: <what in spec or scout briefing suggests it>.
Scope: <files and modules around the change; read nothing beyond their direct callers and callees>.
Scout briefing: <attached | none>. Test pathspec: <pathspec>.
Other units (ignore): <list>.
```

## Design rethink (`dl-architect`, rethink mode)

```
Mode: rethink. Unit <name>, round <N>. Worktree <path>, base <sha>.
Diff: `git -C <path> diff <base>`; size so far: code <+A −R>, tests <+A −R>.
Trigger: <reviewer's DESIGN line, verbatim>. Scope: code the diff and these findings touch.
Open findings: <ids + one line each>. Accepted fixes: <ids>.
Architecture map: <path | none>. Contract: <docs>. Repo rules: <absolute path>.
Other units and their files: <list>.
```

## Reviewer, round 1 (`dl-reviewer`)

```
Unit <name>, round 1. Worktree <path>, base <sha>.
Diff: `git -C <path> diff <base>`. Contract: <docs>. Other units (ignore): <list>.
Repo rules: <absolute path of the rules file>.
Bar: critical/major/minor all count; nits are optional.
Mode: <feature | simplify: lenses Intent, Correctness (behaviour preserved), Simplicity, Duplication>.
Architecture map: <path | none>. Size: code <+A −R>, tests <+A −R>; budget <budget>.
Rejected design proposals: <one line + user's reason each | none>.
Severity scale: <the table from SKILL.md §1>
Lenses: <all | the subset this reviewer takes>.
Check especially: <risk list for this unit>
Threat model: <who is untrusted and what they control | none>
Probes: <command that runs one of your own probe files | none: cannot run here>. Never the full test suite or the project's tests. Keep each probe that proves a finding and name its path and run command in the finding; its fixer deletes it.
Tier of the code's author: <Light | Standard | Deep>.
```

## Re-review (same reviewer session)

```
Round <N+1>. The fixer (<tier>) addressed your findings in the working tree.
Answers to your questions: <list, or none>.
Your "Not checked" items, now run: <check: result, or none>.
Fixers' design friction: <notes, or none>.
Verify each prior finding is resolved: <ids + one-line what changed>.
Accepted as is: <ids>. Rejected by the orchestrator: <id: reason>.
Then re-read the whole current diff; later-round rule applies.
Judge the `TIER:` line against the fixer's tier.
```

## Exhaustive-enumeration helper (the harness's read-only scout)

```
Enumerate EVERY <string/const/call site> that <reaches X>. Be exhaustive; say which grep
patterns you used. Output: table value → file:line. Change nothing.
Unsure what counts as reaching <X>, or blocked? Ask the orchestrator if you can message
it; otherwise list the open cases under `## Unsure` instead of guessing.
```

## Minor sweep (dispatched through tiered-fanout to the tier's agent)

```
# Target
Worktree `<absolute path>`. Files you may edit: <list>.
Items, each with the orchestrator's decision: <id: decision>.
# Change
For every item: check it still holds on the current tree, then apply the decision. If it
no longer holds, report `stale: <reason>` instead of editing. Repeats across rounds = one
fix. Re-read a file right before each edit.
Final answer: table item → fixed (file:symbol) | stale (reason), plus tests added.
```
