# Prompt templates

Replace `<…>`. Keep the severity bar and stop condition in every reviewer prompt. The
role rules (read-only, ask the orchestrator, output format, `TIER:` and `VERDICT:` lines)
live in the `dl-reviewer` agent; implementer, fix and runner tasks are in `tiered-fanout`
§4. The orchestrator runs `git -C <path> add -N .` before sending the round-1 or
re-review prompt, so the diff shows new files. Without plugin agents, paste the agent
file's body above each prompt and set the model as `tiered-fanout` §4 says.

## Reviewer, round 1 (`dl-reviewer`)

```
Unit <name>, round 1. Worktree <path>, base <sha>.
Diff: `git -C <path> diff <base>`. Contract: <docs>. Other units (ignore): <list>.
Bar: critical/major/minor all count; nits are optional.
Severity scale: <the table from SKILL.md §1>
Check especially: <risk list for this unit>
Tier of the code's author: <Light | Standard | Deep>.
```

## Re-review (same reviewer session)

```
Round <N+1>. The fixer (<tier>) addressed your findings in the working tree.
Answers to your questions: <list, or none>.
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
