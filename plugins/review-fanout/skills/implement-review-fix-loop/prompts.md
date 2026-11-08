# Prompt templates

Replace `<…>`. Keep severity bar and stop condition in every prompt.

## Implementer

```
# Target
Worktree `<absolute path>`. Spec: <decision/doc ids>. Files you may edit: <list>.
Other units' areas (do not touch): <list>.
# Change
1. <numbered steps, binding decisions inline>
# Tests
- <behaviour per rule; at least one regression test that fails before the fix>
# Acceptance
Code + tests + docs in the worktree, uncommitted.
Rules: absolute paths only. Do NOT run the full gate, formatters or commit; the
orchestrator verifies. You may run your own new test once. If you must touch a file
outside the list, say so and why in the report.
Final report: 1. files changed 2. what each change does 3. tests and what each proves
4. deviations 5. out of scope
```

## Reviewer, round 1

```
Unit <name>, round 1. Worktree <path>, base <sha>.
Review ONLY changed lines: `git -C <path> diff <base>`. Read-only: no edits, no commits,
no build/test runs. Contract: <docs>. Other units (ignore): <list>.
Bar: critical/major/minor all count; nits are optional. Reserve critical/major for real
correctness, regression, data-loss, security or rule violations.
Check especially: <risk list for this unit>
Tests: for each new test name the plausible bug that makes it fail; flag any test that
would pass with a buggy implementation.
Output: each finding as `### <severity> · <file>:<line> · <title>` + evidence + concrete
fix. Out-of-diff issues in a final `## Out of scope` section (not findings).
Last line exactly `VERDICT: PASS` (nothing at or above minor) or `VERDICT: FIX`.
```

## Findings → implementer (same session)

```
Review round <N> on your unit: <n> critical, <n> major, <n> minor.
Fix in the working tree and do NOT commit (the orchestrator commits). Binding decisions:
- <finding id>: <decision, with evidence>
Add a regression test that fails before the fix; prove it by temporarily swapping in
the buggy body, seeing it fail, then reverting. Do not run the full gate.
Report: `## Finding map` (finding → file:line or test, or `rejected: <reason>`),
`## Notes for later rounds`, `## Pre-existing (not fixed)`.
```

## Re-review (same reviewer session)

```
Round <N+1>. The implementer addressed your findings in the working tree.
Verify each prior finding is resolved (repro where possible): <ids + one-line what changed>.
Accepted as is: <ids>. Then re-read the whole current diff for anything the fix introduced.
Later-round rule: block only on regressions caused by this unit, unmet requirement
clauses, or defects on lines it added/changed; mark the rest `pre-existing:` in Out of scope.
Same output format; end with a VERDICT line.
```

## Exhaustive-enumeration helper (read-only)

```
Enumerate EVERY <string/const/call site> that <reaches X>. Be exhaustive; say which grep
patterns you used. Output: table value → file:line. Change nothing.
```

## Minor sweep (agents split by file ownership)

```
Scope: fix left-out minors that point to inefficiencies, stale documentation,
design-documentation divergence, missing features, duplication. Out of scope: test-style
nits, missing-test findings, items needing an operator decision (report those).
For every item: verify it still holds on the current tree; fix it; or reject with a
one-line reason. Repeats across rounds = one fix.
Never edit a file another agent owns; ask the owner via message with the exact change.
Re-read a file right before each edit. Do not run the gate, do not commit.
Final answer: table item → fixed (file:symbol) | rejected (reason) | needs operator (why),
plus tests added.
```
