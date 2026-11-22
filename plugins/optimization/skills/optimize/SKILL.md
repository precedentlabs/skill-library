---
name: optimize
description: Use when the user wants something measurably improved (speed, latency, memory, binary or index size, build or test time, token or API cost) and wants it done as a disciplined, possibly unattended loop - profile, one change at a time, measure, accept or reject, regression gate, record - until nothing worthwhile is left. The goal is given after the command, for example /optimization:optimize cut cold start time. Not for one-off micro-fixes or for optimizing without a way to measure.
argument-hint: 'goal, e.g. "cut cold-start time" or "reduce API token spend"'
---

# Optimize: $ARGUMENTS

**Goal:** $ARGUMENTS

Goal line empty or still placeholder → use arguments given after skill name (oh-my-pi appends them as trailing `User:` line); none → ask user for goal before anything else. Do not guess one.

Metric-driven loop. Every change justified by measurement before, kept or reverted by measurement after. No change without profile line naming it; no merge without proof §0 invariants hold; no claim without a number.

## 0. Frame the goal (before touching code)

Write short plan file, kept with project's notes:

|Item|Content|
|---|---|
|Objective|metric(s), unit, direction, workload(s) measured on|
|Invariants|what must not change, declared per goal: output equivalence (when goal is speed or memory), public behaviour, compatibility, durability, security properties. Goal like token cost or binary size may change output by design: then declare which properties must still hold instead|
|Guardrails|metrics that must not worsen while objective improves (memory, size, other paths, cost)|
|Boundaries|needs **operator decision**, never unilateral: project-rule exception, durability or concurrency trade-off, new dependency, architectural change|
|Stop rules|§6, plus any user target ("2x faster", "under 200 ms")|
|Autonomy|user away? Then no pushes, no questions, decisions go on list for later|

Ask user only about genuinely ambiguous points (which metric, which workload), once, batched. User away → pick conservative default, list as assumption. Goal with no measurable form ("make it better") → turn into metric first.

## 1. Build the measuring stick

1. **Baseline = named commit**, built into own worktree or output directory. Never compare against build directory whose commit you did not record: stale binary once made no-op change look like gain.
2. **Representative workloads**: real or pinned data, small/medium/large cases. One workload proves nothing.
3. **Harness**: repeated rounds, old and new **interleaved**. Report minimum for wall time; CPU time for single-thread work (robust to other load); p50/p95 over N operations for latency. Record machine, load, temperature, tool versions in every result file.
4. **Noise floor**: run baseline vs baseline first (A/A). Its spread = bar a change must clear.
5. **Invariant oracles**: per §0 invariant, a check that can fail. Output equivalence an invariant → freeze digest of full baseline output on every workload ("golden"). Always add project's test suite and any correctness corpus.
6. **Harness sees the effect?** Standard benchmark cannot observe what profile predicts → write micro-harness that can, keep it with results; note benchmark gap, do not hide it.
7. **Published latency numbers: single-threaded/uncontended**; benchmark's parallel default can distort latency 2-4x.

No measurements while builds, test suites, or other agents compete for machine. Loop serial by design. Subagents MAY do read-only profile analysis, candidate research, develop-loop review and fix rounds (§3 step 5); never concurrent timing. Re-measure only after loop's agents finish.

## 2. Profile first

- Sampling profiler on real workload, line-table resolution, single- and multi-threaded; rank stages by share. Non-CPU goals: "profile" = breakdown by contributor (tokens by prompt part, bytes by table, cost by call site).
- Also measure what standing metrics do **not** cover: peak memory of every command, on-disk size, startup. Speed-ups often move cost there (a regression found only when someone checked peak memory of cold path).
- Build ranked candidate list. Each candidate cites profile line, its share, predicted gain, risk. Prefer high share, low risk, small diff.

## 3. One iteration = one change

1. Branch from main in fresh worktree (`perf-<name>`). **Smallest** version of the idea; larger version = own later step, measured against this one.
2. Optional: isolated micro-measurement of the idea first (effect alone, before wiring).
3. Build old and new from named commits; measure targeted effect, interleaved.
4. **Regression gate**: every §0 invariant holds (golden digest equal on every workload when equivalence is one), correctness corpus equal, full project gate green. Behavioural test for new rule (property/round-trip tests for "same order, same bytes" claims). Draft rejected by property test = wrong draft, not flaky test.
5. **Develop-loop review** of accepted change (requires `develop-loop` plugin): run `implement-review-fix-loop` from its optimize entry (`implement-review-fix-loop` §0): loop's review and fix steps (`implement-review-fix-loop` §2 steps 3–8) on `git -C <worktree> diff main`, this goal's §0 plan as contract document, until verdict meets bar; orchestrator commits fixes on perf branch. Loop's integration and finish steps do not apply; out-of-scope findings go to its backlog. After loop passes, re-run step 4 on fixed branch; fix touched measured path → repeat step 3 too and re-apply §4 (change no longer qualifying → rejected, recorded like any other). Review does not reach bar within loop's round cap → skip loop's takeover round, reject change: record with open findings (§7), remove worktree; unattended → list under explicit asks (§9).
6. Record (§7), then merge `--no-ff`, remove worktree, delete branch. Main clean after every step.
7. **Re-profile main.** Next candidate comes from new profile, not old one.

## 4. Accept / reject

Accept only if all hold:

- predicted metric moves **outside noise floor**, in **predicted direction**, on **more than one workload**;
- every §0 invariant holds (equivalence 100 % where declared, tests, corpus);
- guardrail metrics did not worsen, or worsening explained and judged acceptable;
- default or tuning setting changes only with its justifying measurement in same commit.

Reject (and `git revert` if already merged) when: deltas have mixed signs inside spread; effect vanishes in clean A/B; invariant check fails. Record rejections with data exactly like acceptances; prevents retrying the idea.

Judgement rules:

- Suspiciously good first result = confound until clean A/B says otherwise (stale binary, warm cache, shared build dir, different load).
- Side-metric shift: investigate, do not shrug off: repeat it, find mechanism (e.g. timer tick phase), compare to its threshold.
- Thresholds from measured crossover curve, not a guess.
- Absolute numbers not comparable across sessions; interleaved A/B comparisons are.
- Never trade an invariant for speed without operator decision.

## 5. Delegation

Loop itself serial. Subagents for: reading profiles, researching candidate techniques, writing micro-harness, develop-loop review of every accepted diff (§3 step 5). Never for timing runs.

## 6. Stop rules

Stop when any true, then write cumulative report:

- next profile-ranked candidate under about 10 % of its path, or in third-party code you cannot change;
- best remaining candidates need **operator decision** (rule exception, durability/concurrency trade-off, new dependency, architecture): list each with its gain and trade-off, hand back;
- three consecutive iterations rejected;
- user's target met;
- budget (time, cost) spent.

State stop reason explicitly. "Nothing left to optimize" rarely literally true.

## 7. Records

Per step (accepted or rejected), in project's decision log: *Conflict* (profile line, quantified), *Decision*, *Why* (numbers). Plus results note: method, tables, "No regression" section, directory with raw data and **scripts used**, so tooling outlives scratch directory. Write each step's record when step finishes, to temporary file then renamed ⇒ interrupted run never leaves half-written record, always has last complete step to resume from.

## 8. Unattended mode

- Do not push; leave main clean, every step merged or reverted, never half done.
- Do not stop to ask; accumulate operator decisions, continue with what is safe.
- Machine sleeps or job killed → resume from last recorded step.

## 9. Final report

1. One-line status: commit, clean tree, whether anything pushed.
2. Steps table: id, change, measured effect, fate (rejected steps included, with why).
3. Cumulative table vs named pre-loop build, per workload, **before and after as separate numeric columns** (an "a -> b" cell once broke a chart renderer).
4. Invariants: check results per step, gate status, develop-loop's last `VERDICT:` line per accepted step.
5. What profiles leave: remaining items with shares, each tagged *needs decision* or *diminishing*.
6. Explicit asks (rule exceptions, follow-ups, push).

## Pitfalls seen

- Stale baseline binary measured a different change's gain.
- Benchmark default parallelism inflated latency 2-4x; published run needed single threading.
- Speed-up quietly raised peak memory on path no standing metric watched.
- Standard benchmark blind to product case (one-line edits hid lazy-decode gain).
- Sampling-timer phase artefacts read as regressions.
- Thermal and load drift between sessions: only interleaved comparisons valid.
- Hidden fixed cost found only by profile (empty parallel loop still created thread pool).
