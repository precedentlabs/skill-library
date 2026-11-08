---
name: implement-review-fix-loop
description: Use when the user asks an agent to implement a change and then loop review → fix until no critical, major or minor finding is left ("repeat until clean", "until nothing blocks"). Covers unit partitioning, severity definitions, the per-round protocol, convergence and stop rules, scoping reviews to the diff, a backlog for out-of-scope findings, worktrees, and the final gate. Not for a one-shot review or for fixing an already-finished review (use review-fix-fanout).
---

# Implement → review → fix, until clean

The orchestrator decides, gates and commits. Subagents implement, review and fix.
Nothing is "done" on a subagent's word: the loop ends only on a reviewer verdict
**plus** a green gate run by the orchestrator.

## 0. Pin the contract before any code

- Decisions the spec left open are taken (or asked with 2–4 concrete options) and
  **written down first** (decision record / design doc, committed). An implementer
  never guesses them.
- Split the work into **units** with disjoint file sets. Order units by risk (security
  fixes before functional changes). One unit = one implement/review/fix loop.
- One read-only scout first when the code map is unknown; implementers read its briefing
  instead of exploring.
- One worktree per unit when units run in parallel (§6).

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
not re-raise a finding the fixer rejected *with a reason* unless they show why the reason
is wrong, and must not reopen a fix an earlier round accepted.

## 2. The per-round protocol

1. **Implement.** One implementer per unit. Brief: `# Target` (files, worktree absolute
   path), `# Change` (numbered, binding decisions), `# Tests` (behaviour per rule; a
   regression test that fails before the fix), `# Acceptance`. Rules: use absolute
   paths, do not run the full gate/formatters (orchestrator does), never commit,
   report `files changed / what each change does / tests and what each proves /
   deviations / out of scope`.
2. **Orchestrator gate + spot-read.** Run build/lint/tests yourself; read the diff. Red
   → send the exact failure back to the implementer. Never review red code.
3. **Review.** Fresh read-only reviewer(s) scoped to the diff (§3). Required output:
   findings with severity, `file:line`, evidence, fix; a `## Out of scope` section; last
   line `VERDICT: PASS` (nothing at or above the bar) or `VERDICT: FIX`.
4. **Triage every finding yourself**: fix / reject with a reason / the spec is wrong →
   write a decision and amend / accept as is. You make the design call; do not hand the
   fixer an open question.
5. **Fix.** Default: send to the **same implementer session** (it keeps context): counts, each
   finding with the decision marked binding, "edit the working tree, do not commit", a regression
   test that fails before the fix, report diff + results. Fixers prove each new test by
   temporarily swapping in the plausible bug, seeing it fail, then reverting.

   **Large or mixed rounds → fan out.** When a round's findings span several files or
   effort classes (docs wording, a test, a refactor), or the user asked for model tiering,
   run this step with the `review-fix-fanout` skill: its triage (§1), one-owner-per-file
   partition (§2), task template (§3) and one-batch spawn (§4) route each finding class to
   the cheapest adequate model tier. Inside the loop: its fixers also never commit, and its
   own gate/report (§5–6) are replaced by steps 6–8 here; the orchestrator's triage in step 4
   is its §1.
6. **Orchestrator gate + read the fix** before re-review.
7. **Re-review.** Same reviewer session (or a fresh one for independent eyes on later
   rounds): verify each prior finding is resolved (repro where possible) **and**
   re-read the whole current diff for anything the fix introduced.
8. Repeat 4–7 until the verdict meets the bar.

"Same session" assumes the harness can message a running or idle subagent. If it cannot,
spawn a new one and hand it the previous report, the findings and the diff command; the
protocol is unchanged.

**Cosmetic tail.** When the last open item is a comment, a doc line or a format fix,
the orchestrator fixes it inline and confirms with the gate instead of another review
round. Record that it was not re-reviewed. Anything touching behaviour gets a review.

**Round cap.** Three automatic fix rounds per unit. Still failing → stop, summarise
the remaining findings, and make a **human round** (read review, verify each finding,
fix in the working tree, gate; the orchestrator commits), then run the review again: human fixes
regress too.

## 3. Reviewer setup

- Read-only: no edits, no commits, no build/test/gate runs (orchestrator owns those). Allow
  scratch edits only if they are reverted.
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

## 4. Backlog for everything out of scope

Out-of-diff findings never block and never get fixed in this loop. They go to
`backlog.md` at the repo root, **excluded from git** (`.git/info/exclude`, not
`.gitignore`, so the exclusion itself is not committed). Each entry: where, what, which
round found it. Triage the backlog after the loop; a post-loop **minor sweep** (below) is
the cheap way to close it.

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
   (it finds near-copies that parallel agents wrote independently; fix by extracting one
   helper per pair, not by weakening assertions).
2. **Live smoke**: run the real system on a throwaway instance and exercise the changed
   paths in a browser/CLI. Reviews that read code miss rendering and integration bugs;
   smoke tests have caught defects after several clean review rounds.
3. **Minor sweep** for leftovers collected in the backlog/last PASS reviews: scope it
   (inefficiency, stale docs, design-doc divergence, missing features, duplication),
   skip test-style nits and anything needing an operator decision, split by file
   ownership across agents, "verify the item still holds → fix or reject with a
   one-line reason", then one gate and one commit.
4. Final report: headline (what landed, commit range, gate result, smoke result) → how it
   ran (rounds per unit) → one bullet per user-visible behaviour with decision ids →
   **Needs your attention** (rejected items, divergences, backlog summary, anything not
   exercised).

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

See `prompts.md` for copy-ready implementer, reviewer, fix and re-review prompts.
