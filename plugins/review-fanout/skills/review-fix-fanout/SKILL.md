---
name: review-fix-fanout
description: Use after a parallel code review of a large uncommitted change produced findings and the user asks to fix them with subagents (optionally tiered by model). Covers triage, file-ownership partitioning, model tiering, README/doc reconciliation, and one final gate. Not for a single small fix or for running the review itself.
---

# Review findings → fix fanout

Turn reviewer output into fixes with parallel subagents without file collisions,
wasted model spend, or a gate that fails at the end.

## 1. Triage the findings

Group every finding by **owning file**, then classify by effort:

| Class | Examples | Default model tier |
|---|---|---|
| Mechanical / docs | README wording, comment fixes, doc table rows, deploy-script comments | cheapest (haiku-class) |
| Moderate, pattern-following | add a test in an existing harness, bound a resource with an existing primitive, adjust one function | mid (sonnet-class, medium) |
| Design or cross-cutting | refactor a duplicated primitive, change startup/migration ordering, wire-format or security invariants, a fix with two plausible directions | strongest (opus-class, medium) |

If the user names a tiering (e.g. "docs → haiku, medium → sonnet, complex → opus"), follow
it exactly. Only use models the harness lists as approved; if one is unavailable, stop
and say so, never substitute.

Decide per finding whether to fix or document. When a finding is a contract
mismatch with two valid resolutions (fix code vs. fix docs), pick the conservative
one, state it in the task, and say so in the final report.

## 2. Partition by file, one owner per file

- Every file has exactly one task that may edit it. List owned files in the task and
  forbid touching others.
- Docs that several fixes touch (README, AGENTS.md) belong to **one docs task or the
  parent**, never to the code tasks. Code tasks must *report the wording* they need
  instead of editing the doc.
- If a fix forces a minimal edit in another task's file (e.g. a new struct field at a
  call site), allow it explicitly and require the agent to report it.
- Unify findings that share a mechanism into one task (e.g. two fixes in one module
  that must not be designed separately).

## 3. Write self-contained tasks

Subagents start blank. Put shared rules in `context` once (repo rules file, "do not run
the build/gate/formatters", "report what the parent must still do"). Each task needs:

- `# Target`: files, non-goals
- `# Change`: numbered steps with the exact symbol/line hints from the review, the chosen
  resolution, and the constraints that make it correct (e.g. "refused attempts must not
  count toward the throttle", "Claude-Code-shaped bodies must pass byte for byte")
- `# Acceptance`: observable result, tests to add (and that a regression test must fail
  before the fix), wording to report back

Pass the `solutionSpace` honestly: "wording given" for docs, "design open within
constraints" for refactors.

## 4. Spawn once, batch, then integrate

Spawn all independent tasks in **one** `tasks[]` batch. Do not poll; do productive
work while they run. The one thing the parent should do meanwhile: apply the doc
wording that agents report, serialized after the docs task finishes (editing a doc
while its owner is still running causes clobbered lines).

Verify doc edits by reading the result. Replacing a line range with fewer lines than
the range silently eats neighbouring text; re-read the region after each range edit.

## 5. One gate, run by the parent

Subagents do not build. After every task is back, run the project's full gate exactly
once, in the repo's documented order (format, lint, tests, other checks,
duplicate/clone detection). Then expect and handle:

1. **Duplicate-code / clone detectors** flag the near-identical test setups that
   parallel agents write independently. Send them to a small agent (mid tier) or fix
   them yourself: extract one helper per pair, never weaken assertions.
2. **Lint nursery noise** on helpers added for tests (e.g. redundant visibility).
3. **A new cap/guard breaks an old concurrency test.** When a new bound changes the
   observable mix of outcomes (e.g. some attempts now get 503), adapt the test to the
   invariants that still hold (checked ≤ limit, counted == checked, outcomes sum to
   total). Say so in the report; do not silently loosen a test that exercises a valid
   case without stating why the old expectation no longer applies.
4. Re-run the full gate after the last edit; one edit invalidates it.

## 6. Report

Per finding: fixed / documented / not done, with the choice made. Then:
- what the gate showed (counts, not "passes")
- anything unexercised (not run live, behaviour only structurally testable)
- decisions left open to the user (e.g. "misleading message kept; want a distinct one?")
- if an experiment on model tiering: one line per tier on how it did

## Pitfalls seen

- Agents asked not to run cargo cannot catch their own breakage: budget a fix round.
- Two agents sharing a test module both add helpers → duplicates; assign test regions.
- A reviewer's "fix" option that contradicts the contract doc (README) loses; the doc
  is authoritative, so fix whichever side the doc says is wrong, deliberately.
- Don't spawn more agents than there are real file-disjoint slices.
