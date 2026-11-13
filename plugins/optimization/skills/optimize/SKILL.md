---
name: optimize
description: Use when the user wants something measurably improved (speed, latency, memory, binary or index size, build or test time, token or API cost) and wants it done as a disciplined, possibly unattended loop - profile, one change at a time, measure, accept or reject, regression gate, record - until nothing worthwhile is left. The goal is given after the command, for example /optimization:optimize cut cold start time. Not for one-off micro-fixes or for optimizing without a way to measure.
argument-hint: 'goal, e.g. "cut cold-start time" or "reduce API token spend"'
---

# Optimize: $ARGUMENTS

**Goal:** $ARGUMENTS

If the goal line above is empty or still shows the placeholder, use the arguments given
after the skill name instead (oh-my-pi appends them as a trailing `User:` line); without
any, ask the user for the goal before doing anything else. Do not guess one.

A metric-driven loop. Every change is justified by a measurement before it and kept or
reverted by a measurement after it. No change without a profile line that names it; no
merge without proof that the invariants declared in §0 hold; no claim without a number.

## 0. Frame the goal (before touching code)

Write down, in a short plan file kept with the project's notes:

| Item | Content |
|---|---|
| Objective | the metric(s), unit, direction, and the workload(s) it is measured on |
| Invariants | what must not change, declared per goal: output equivalence (when the goal is speed or memory), public behaviour, compatibility, durability, security properties. A goal such as token cost or binary size may change output by design: then declare which properties must still hold instead |
| Guardrails | metrics that must not get worse while the objective improves (memory, size, other paths, cost) |
| Boundaries | what needs an **operator decision**, never a unilateral one: a project-rule exception, a durability or concurrency trade-off, a new dependency, an architectural change |
| Stop rules | §6, plus any target the user gave ("2x faster", "under 200 ms") |
| Autonomy | is the user away? Then: no pushes, no questions, decisions go on the list for later |

Ask the user only about what is genuinely ambiguous (which metric, which workload), once,
batched. If they are away, pick the conservative default and list it as an assumption.
A goal with no measurable form ("make it better") must be turned into a metric first.

## 1. Build the measuring stick

1. **Baseline = a named commit** built into its own worktree or output directory. Never
   compare against a build directory whose commit you did not record: a stale binary
   once made a no-op change look like a gain.
2. **Representative workloads**: real or pinned data, covering small/medium/large
   cases. One workload proves nothing.
3. **Harness**: repeated rounds with old and new **interleaved**; report the minimum for
   wall time, CPU time for single-thread work (robust to other load), p50/p95 over N
   operations for latency. Record machine, load, temperature, tool versions in every
   result file.
4. **Noise floor**: run baseline against baseline first (A/A). Its spread is the bar a
   change must clear.
5. **Invariant oracles**: for every invariant declared in §0, a check that can fail. When
   output equivalence is an invariant, freeze a digest of the full output from the baseline
   on every workload ("golden"). Always add the test suite and any correctness corpus the
   project has.
6. **Does the harness see the effect?** If the standard benchmark cannot observe what
   the profile predicts, write a micro-harness that can and keep it with the results;
   note the benchmark gap instead of hiding it.
7. **Latency numbers for publication run single-threaded/uncontended**; a benchmark's
   parallel default can distort latency by 2-4x.

Do not run measurements while builds, test suites or other agents compete for the
machine. This loop is serial by design; subagents may do read-only profile analysis,
candidate research, and the develop-loop review and fix rounds (§3 step 5), never
concurrent timing: re-measure only after the loop's agents have finished.

## 2. Profile first

- Use a sampling profiler on the real workload, at line-table resolution, single- and
  multi-threaded; rank stages by share. For non-CPU goals the "profile" is a breakdown
  by contributor (tokens by prompt part, bytes by table, cost by call site).
- Also measure what the standing metrics do **not** cover: peak memory of every command,
  on-disk size, startup. Speed-ups often move cost there (a regression was found only when
  someone looked at peak memory of the cold path).
- Build a ranked candidate list. Each candidate cites the profile line, its share,
  the predicted gain, the risk. Prefer high share, low risk, small diff.

## 3. One iteration = one change

1. Branch from main in a fresh worktree (`perf-<name>`). The **smallest** version of the
   idea; the larger version is its own later step, measured against this one.
2. Optional isolated micro-measurement of the idea first (the effect alone, before wiring).
3. Build old and new from named commits; measure the targeted effect, interleaved.
4. **Regression gate**: every §0 invariant holds (the golden digest equal on every workload
   when equivalence is one), correctness corpus equal, full project gate green. A behavioural test for the new rule (property/round-trip
   tests for "same order, same bytes" claims). A draft the property test rejects is a
   wrong draft, not a flaky test.
5. **Develop-loop review** of the accepted change (requires the `develop-loop` plugin):
   run `implement-review-fix-loop` from its optimize entry (`implement-review-fix-loop` §0):
   the loop's review and fix steps (`implement-review-fix-loop` §2 steps 3–8) on
   `git -C <worktree> diff main`, with this goal's §0 plan as the contract document,
   until the verdict meets the bar; the orchestrator commits the fixes on the perf branch.
   The loop's integration and finish steps do not apply; out-of-scope findings go to its
   backlog. After the loop passes, re-run step 4 on the fixed branch; when a fix touched
   the measured path, repeat step 3 as well and re-apply §4 (a change that no longer
   qualifies is rejected and recorded like any other). If the review does not reach the
   bar within the loop's round cap, skip the loop's takeover round and reject the change:
   record it with its open findings (§7) and remove the worktree; when unattended, list it
   under explicit asks (§9).
6. Record (§7), then merge `--no-ff`, remove the worktree, delete the branch. Main stays
   clean after every step.
7. **Re-profile main.** The next candidate comes from the new profile, not the old one.

## 4. Accept / reject

Accept only if all hold:

- the predicted metric moves **outside the noise floor**, in the **predicted direction**,
  on **more than one workload**;
- every §0 invariant holds (equivalence 100 % where declared, tests, corpus);
- guardrail metrics did not worsen, or the worsening is explained and judged acceptable;
- a default or tuning setting changes only with the measurement that justifies it in the
  same commit.

Reject (and `git revert` if already merged) when deltas have mixed signs inside the
spread, the effect vanishes in a clean A/B, or an invariant check fails. Rejections are
recorded with their data exactly like acceptances; they prevent the idea being retried.

Judgement rules:

- A suspiciously good first result is a confound until a clean A/B says otherwise
  (stale binary, warm cache, shared build dir, different load).
- A side-metric shift is investigated, not shrugged off: repeat it, find the mechanism
  (for example a timer tick phase), compare to its threshold.
- Take a threshold from the measured crossover curve, not a guess.
- Absolute numbers are not comparable across sessions; interleaved A/B comparisons are.
- Never trade an invariant for speed without an operator decision.

## 5. Delegation

The loop itself is serial. Use subagents for: reading profiles, researching candidate
techniques, writing the micro-harness, and the develop-loop review of every accepted diff
(§3 step 5). Never for timing runs.

## 6. Stop rules

Stop when any is true, then write the cumulative report:

- the next profile-ranked candidate is under about 10 % of its path, or in third-party code
  you cannot change;
- the best remaining candidates need an **operator decision** (rule exception,
  durability/concurrency trade-off, new dependency, architecture): list them with the
  gain each would bring and the trade-off, and hand them back;
- three consecutive iterations were rejected;
- the user's target is met;
- the budget (time, cost) is spent.

State the stop reason explicitly. "Nothing left to optimize" is rarely literally true.

## 7. Records

Per step (accepted or rejected), in the project's decision log: *Conflict* (the profile
line, quantified), *Decision*, *Why* (the numbers). Plus a results note with method,
tables, a "No regression" section, and a directory with the raw data and **the scripts
used**, so the tooling outlives a scratch directory. Each step's record is written when
that step finishes, to a temporary file that is then renamed, so an interrupted run never
leaves a half-written record and always has a last complete step to resume from.

## 8. Unattended mode

- Do not push; leave main clean and every step merged or reverted, never half done.
- Do not stop to ask; accumulate operator decisions and continue with what is safe.
- If the machine sleeps or the job is killed, resume from the last recorded step.

## 9. Final report

1. One-line status: commit, clean tree, whether anything was pushed.
2. Steps table: id, change, measured effect, fate (rejected steps included, with why).
3. Cumulative table against the named pre-loop build, per workload, **before and after as
   separate numeric columns** (an "a -> b" cell broke a chart renderer once).
4. Invariants: the check results per step, gate status, and the develop-loop's last
   `VERDICT:` line for each accepted step.
5. What the profiles leave: remaining items with shares, each tagged *needs decision*
   or *diminishing*.
6. Explicit asks (rule exceptions, follow-ups, push).

## Pitfalls seen

- Stale baseline binary measured a different change's gain.
- Benchmark default parallelism inflated latency 2-4x; the published run needed single
  threading.
- Speed-up that quietly raised peak memory on a path no standing metric watched.
- Standard benchmark blind to the product case (one-line edits hid a lazy-decode gain).
- Sampling-timer phase artefacts read as regressions.
- Thermal and load drift between sessions: only interleaved comparisons are valid.
- Hidden fixed cost found only by profile (an empty parallel loop still created a thread
  pool).
