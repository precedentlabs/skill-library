---
name: implement-review-fix-loop
description: Use for all implementation work - any request to implement, change or fix code, tests or docs, a batch selected by triage-findings, or an accepted optimize change - and loop review → fix until no critical, major or minor finding is left ("repeat until clean", "until nothing blocks"). Covers unit partitioning, severity definitions, the per-round protocol (implement and fix steps run through tiered-fanout), convergence and stop rules, scoping reviews to the diff, a backlog for out-of-scope findings, worktrees, and the final gate. Not for a one-shot review with no changes, or for deciding which findings to fix (triage-findings).
---

# Implement → review → fix, until clean

The orchestrator decides, gates and commits. Subagents implement, review and fix.
Nothing is "done" on a subagent's word: the loop ends only on a reviewer verdict
**plus** a green gate owned by the orchestrator (run by it, or by `dl-runner` whose raw
output it reads and judges).

Place in the hierarchy: `triage-findings` selects a batch → this loop → `tiered-fanout`
does the implement and fix work, each item on the model tier its difficulty needs. The
loop never calls triage; out-of-scope findings reach it through the backlog (§4).

**All implementation work goes through this loop**: features, fixes, triage batches,
accepted `optimize` changes, doc and test changes. A small change runs the same loop at
its smallest (one unit, one reviewer), never a skipped review. Only runs that change no
files (tests, the gate, deployments) use `tiered-fanout` without it.

## 0. Pin the contract before any code

- Decisions the spec left open are taken (or asked with 2–4 concrete options) and
  **written down first** (decision record / design doc, committed). An implementer
  never guesses them.
- Split the work into **units** with disjoint file sets. Order units by risk (security
  fixes before functional changes). One unit = one implement/review/fix loop.
- One read-only scout first when the code map is unknown (the harness's built-in one:
  Claude Code `Explore`, oh-my-pi `scout`); implementers read its briefing instead of
  exploring.
- One worktree per unit when units run in parallel (§6).
- **Entry from triage.** An approved batch from `triage-findings`: each group in the batch
  (rows sharing an owning file or a root cause) becomes one unit and stays whole; a sweep
  group becomes one sweep unit. The table's difficulty hints go to `tiered-fanout` as tier
  hints.
- **Entry from optimize.** An accepted `optimize` change is one unit, already implemented
  and gated in its perf worktree: start at §2 step 3 on `git -C <worktree> diff main`, with
  `optimize`'s §0 plan as the contract document, and run steps 3–8 until the verdict meets
  the bar. The orchestrator commits fixes on the perf branch and reports every fix that
  touches the measured path. §5 integration and §7 finish do not apply: out-of-scope
  findings go to the backlog, and `optimize` does the measurement, record and merge. At
  the round cap there is no human round: stop and hand back to `optimize`, which rejects
  the change.

## 1. Stop condition (state it, quote it)

The user's default: **loop until no critical, major or minor finding remains.** Nits
are optional (apply the cheap ones). If the user names a different bar (e.g. only
blocker/major), use theirs. Restate the active bar in the first message to each
implementer and reviewer, and **quote the last verdict line in every status report**.
Never end a turn on a menu ("shall I fix these or open a PR?") while the stop condition
is unmet: keep looping; ask only about things outside the instruction (push, merge).

### Severity scale (put it in every reviewer prompt)

| Severity | Meaning |
|---|---|
| critical / blocker | wrong behaviour, data loss, security hole, broken build/gate, violated MUST rule |
| major | requirement unmet; regression; observable behaviour with no test; a stale *contract* (docs, schema, migration header, another unit's spec); a reimplemented primitive; hot-path cost the rules forbid |
| minor | stale comment/doc wording, near-duplicate test setup, dead code left behind, small simplification |
| nit | taste; optional |

Reviewers are strict but evidence-based: critical/major only for real correctness,
regression, data-loss, security or rule violations, each with `file:line`, evidence and
a concrete fix. Findings the code does not support are not findings.

### Convergence rule for later rounds

"Block on every minor" does not converge if every fix round spawns new comment drift.
From round 2 on, a finding is critical/major/minor **only if** it is (a) a regression
the unit's own changes caused (including a fix breaking an earlier accepted fix),
(b) a requirement clause still unmet, or (c) a defect on a line the unit added or
changed. Anything else is `pre-existing:` and goes to the backlog (§4). Reviewers must
not re-raise a finding the fixer or the orchestrator's triage rejected *with a reason*
unless they show why the reason is wrong, and must not reopen a fix an earlier round
accepted.

## 2. The per-round protocol

1. **Implement.** Dispatch the units through `tiered-fanout`: one implementer per unit,
   spawned as its tier's agent (its §2, §4), briefed with its new-work template (`Spec:` =
   the unit's decision-record ids) plus the active bar. Implementers ask the orchestrator
   when unsure or blocked and send a struggle handoff when the work is beyond them; answer
   or re-assign one step up per its §5.
2. **Orchestrator gate + spot-read.** Run build/lint/tests (yourself or via `dl-runner`,
   reading its raw output); read the diff. Red → send the exact failure back to the
   implementer. Never review red code.
3. **Review.** Fresh `dl-reviewer` agent(s) scoped to the diff (§3). Required output:
   findings with severity, `file:line`, evidence, fix; a `## Out of scope` section; the
   line `TIER: keep` or `TIER: up — <reason>` for the next fix round (§3); last line
   `VERDICT: PASS` (nothing at or above the bar) or `VERDICT: FIX`.
4. **Triage every finding yourself**: fix / reject with a reason / the spec is wrong →
   write a decision and amend / accept as is. You make the design call; do not hand the
   fixer an open question.
5. **Fix.** Through `tiered-fanout`: each finding with its decision marked binding is a
   work item, tiered by difficulty. A reviewer's `TIER: up` sends the unit's next fix round
   one step above the model that wrote the reviewed code, or at the findings' own tier if
   that is higher (its §2 trigger 3), to a fresh fixer. Otherwise findings in files whose
   implementer session is live and at or above the fix tier go back to that session (it
   keeps context); others go to fresh fixers at their tier, or at the tier its §2 sets
   when a trigger applies (its §4 reuse rule). Fixers that struggle send a struggle handoff
   and the work moves one step up (its §2, §5). Fixers edit the working tree, never
   commit, add a regression test that fails before the fix and prove it by temporarily
   swapping in the plausible bug, seeing it fail, then reverting. The fanout reports per
   item (its §8); the gate and its fallout (its §7) are steps 6–8 here; step 4 is its §1.
6. **Orchestrator gate + read the fix** before re-review.
7. **Re-review.** Same reviewer session (or a fresh one for independent eyes on later
   rounds): verify each prior finding is resolved (repro where possible) **and**
   re-read the whole current diff for anything the fix introduced. If the harness cannot
   message the reviewer, spawn a fresh one with the round-1 prompt, its previous report and
   the re-review block.
8. Repeat 4–7 until the verdict meets the bar.

**Cosmetic tail.** When the last open item is a comment, a doc line or a format fix,
the orchestrator fixes it inline and confirms with the gate instead of another review
round. Record that it was not re-reviewed. Anything touching behaviour gets a review.

**Round cap.** Three automatic fix rounds per unit; `tiered-fanout`'s escalation applies
inside them (struggle handoff, two failures at one tier, a reviewer's `TIER: up`, or the
orchestrator's call → one step up). Still failing → stop, summarise the remaining
findings, and make a **human round** (read review, verify each finding, fix in the working
tree, gate; the orchestrator commits), then run the review again: human fixes regress too.

## 3. Reviewer setup

- Spawn the `dl-reviewer` agent (`develop-loop:dl-reviewer` in Claude Code; model routing
  per harness in `tiered-fanout` §4): it carries the read-only rules, the ask rule and the
  output format (findings, `## Out of scope`, `TIER:`, `VERDICT:`). Without plugin agents,
  paste its body at the top of the reviewer prompt and set `opus-5-5:high` with the
  harness's model option. Read-only: no edits, no commits, no build/test/gate runs
  (orchestrator owns those); scratch edits only if reverted.
- **Scope to the diff**, stated as a command: `git -C <worktree> diff <base>` (the working
  tree against the unit's base, so uncommitted changes are included). "Review ONLY changed lines/hunks."
- Give a `Check especially:` list of the risks this unit can break: worst-legal-input
  bounds, shutdown/lifecycle, error shapes, authz, caching, test determinism, etc.
- Run **two reviewers split by lens** on non-trivial units (implementation vs tests,
  or code vs docs/CSS). A single reviewer who already saw the code missed a test-coverage
  major that a second one caught.
- Tests are judged by: *name the concrete pre-fix or plausible-bug behaviour that makes
  it fail; flag any test that would pass with a buggy implementation.*
- Quote the contract documents the reviewer must check against (decision record,
  README, mockup) and say which other units' areas to ignore.
- **Reviewer model: always `opus-5-5:high`** (`dl-reviewer`), whatever tier wrote the
  code. Reviewers are not tiered and never escalate.
- Reviewers ask the orchestrator when the contract or the scope is unclear, instead of
  assuming; the answer goes into the re-review prompt too.
- **Reviewers upgrade the fixer's model.** When the developer's code shows many problems,
  the reviewer writes `TIER: up — <reason>` (else `TIER: keep`) on the line before the
  final `VERDICT:` line, and the next fix round for that unit runs one step above the
  model that wrote the reviewed code (or at the findings' own tier, if higher), on a fresh
  fixer (`tiered-fanout` §2 trigger 3). Default signals: any critical, three or more
  majors, a misread of the design or contract, the same mistake in several places, or a
  prior-round fix that did not hold. The orchestrator applies it; the only exception is
  when its triage rejected the findings the reason rests on, and it records that. When the
  author ran on `opus-5-5:medium` there is no step up: the orchestrator takes the unit
  over or asks the user.

## 4. Backlog for everything out of scope

Out-of-diff findings never block and never get fixed in this loop. They go to
`backlog.md` at the repo root, **excluded from git** (`.git/info/exclude`, not
`.gitignore`, so the exclusion itself is not committed). Each entry: where, what, which
round found it. The backlog belongs to `triage-findings`, which selects the next batch from
it after the loop; the post-loop **minor sweep** (§7) covers only the units' own
leftovers, never backlog entries.

## 5. Parallel units: ownership and integration

- Disjoint file sets; the shared contract (signatures, schemas, decision ids) is written
  before dispatch. A slice that must touch another's file says so in its report.
- Subagents stay within their absolute-path worktree: relative paths landed first edits
  in the main checkout twice. After each wave `git status` in the main checkout must be
  clean.
- Integrate by rebasing each unit's single commit onto the feature branch and
  `merge --ff-only`; conflicts are the orchestrator's, not findings.
- Commit progressively: one focused commit per unit, made by the orchestrator (subagents
  never commit) once the unit's loop passes.

## 6. Worktrees and build cache

- One worktree per unit, created by a tiny script (`git worktree add ../<repo>-wt/<unit>
  -b fix/<unit>`).
- Share the compile/dependency cache so units do not each rebuild from scratch. Rust
  example: seed each worktree's `target/` as a copy-on-write reflink of the main one
  (`cp --reflink=auto -r`), or point all at one `CARGO_TARGET_DIR` or sccache; other stacks:
  a shared package/build cache directory. Cap
  concurrent builds (a lock-slot wrapper, e.g. 2 at once) so parallel units do not
  thrash the machine, and unset environment variables the test suite is sensitive to
  inside the wrapper.
- Remove worktrees and merged branches at the end; this is the step that gets forgotten.

## 7. Finish

1. Full gate once on the integrated result, then the repo's duplicate/clone detector
   (it finds near-copies that parallel agents wrote independently). Its fixes (extract one
   helper per pair, never weaken assertions) run as a fix round: §2 steps 4–8.
2. **Live smoke**: run the real system on a throwaway instance and exercise the changed
   paths in a browser/CLI. Reviews that read code miss rendering and integration bugs;
   smoke tests have caught defects after several clean review rounds.
3. **Minor sweep** for each unit's own leftovers: minors and nits from the units' last
   PASS reviews on lines they changed (backlog entries go to `triage-findings`, never here).
   Scope it (inefficiency, stale docs, design-doc divergence, duplication), skip
   test-style nits and anything needing an operator decision, and decide every item
   yourself before dispatch (§2 step 4). Then run it as one more round: dispatch through
   `tiered-fanout` with the sweep prompt, gate, review the sweep diff, fix per §2 steps
   4–8, and one commit. A sweep never lands unreviewed.
4. Final report: headline (what landed, commit range, gate result, smoke result) → how it
   ran (rounds per unit, tiers used and escalations) → one bullet per user-visible
   behaviour with decision ids → **Needs your attention** (rejected items, divergences,
   backlog summary, anything not exercised).

## Failure modes seen

- Agent stops after a clean-looking round to ask permission → violates the loop; keep going.
- Doc claims drift from code between rounds (a doc says "returns 404 on a missing item"
  after the code started returning 410; a documented limit differs from the constant):
  reviewers must check each doc statement the diff touches against the code.
- Prompt-quoted constants/examples propagate wrongly into every slice: verify wire facts
  with a scout before writing the contract.
- Reviewer by reading cannot prove formatting/line-length: let the formatter decide.
- A human or inline fix at the end is not re-reviewed unless you do it; say so.
- Reviewers re-raising rejected findings burn rounds: require the rejection reason in the
  fix summary (`## Finding map`: finding → `file:line`/test, or `rejected: reason`).

See `prompts.md` for copy-ready reviewer, re-review and minor-sweep prompts; implementer,
fix and runner prompts live in `tiered-fanout` §4.
