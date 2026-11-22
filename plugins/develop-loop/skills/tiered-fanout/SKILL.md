---
name: tiered-fanout
description: Use when implement-review-fix-loop dispatches implement or fix work to parallel subagents, each on the cheapest model tier adequate for its difficulty, or when tests, the gate or a deployment should be run by a cheap runner. Not for code or doc changes outside the develop loop, deciding what to fix (triage-findings), or reviewing.
---

# Tiered fanout: develop or fix with model-tiered subagents

Goal: run decided work through parallel subagents without file collisions, wasted model spend, silent guessing, or a gate failing at the end.

Hierarchy: `triage-findings` selects batch → `implement-review-fix-loop` implements, reviews, fixes it → this skill does implement and fix work. Calls nothing above it.

- **Inside the loop** (all implementation work): subagents never commit; parent dispatches fixes, applies none itself outside the cases listed at top of `implement-review-fix-loop`; loop's per-round triage supplies decisions (§1); loop runs gate (§7 lists expected fallout); §8 feeds loop's report.
- **Standalone: runs only.** Without the loop, use only for runner tasks changing no files (tests, gate, deployments). Any code or doc change, even one-line fix, goes through `implement-review-fix-loop`.

## 1. Inputs: decided work items

Work item: development unit (spec + binding decisions), fix (finding + decision taken on it), or operational run (tests, gate, deployment). Every item arrives decided: no open design question goes to a subagent. Development units and fixes: loop's orchestrator decides. Standalone run: exact commands are the decision.

Contract mismatch with two valid resolutions (fix code vs. fix docs) → pick conservative one, state it in task, say so in report.

## 2. Classify difficulty → model tier

|Tier|Work|
|---|---|
|Light|docs and comment wording, doc table rows, simple tests in an existing harness, mechanical edits (renames, config entries, boilerplate from a given template, call-site migrations to a given API followed by a search for the old name), mechanical lint fixes, reading transcripts or logs and extracting given figures, running tests or the gate and reporting raw output, deployments the user asked for|
|Standard|small to medium coding work: a handler, endpoint or feature following an existing pattern, rewriting one function, a new small primitive module (its call-site migration is a separate Light item), non-trivial tests including missing test cases for decided behaviour (also of concurrency code, when the harness already sets the scenario up), helpers extracted for duplicate-check pairs, bounding a resource with an existing primitive; no complicated algorithms|
|Deep|multi-module work, concurrency and lifecycle (session leases, failover, ordering), complex algorithms, optimisations, startup/migration ordering, wire-format and security invariants, refactoring a shared primitive, fixes with two plausible directions or a measure the spec leaves open, any large task that needs complex reasoning; not the test, dedupe or lint follow-ups of its own items|

- Classify per item, not per batch. Item merged from several (§3) takes highest tier of its parts.
- Later rounds' findings: classify each one by the table, not by tier that wrote the unit. Lint fix or call-site migration → Light; missing test case or helper extracted for duplicate-check pair usually below unit's tier too. Only a finding needing the unit's own reasoning (its concurrency, its design decision) keeps unit's tier. Reviewer's `TIER: up` (trigger 3) raises only findings needing that reasoning.
- **Up one tier** when item changes another module's contract or behaviour of concurrency, persistence or security code, has no existing pattern to copy, or its design is open within constraints. Test of already-decided behaviour does not count as changing it.
- **Down one tier** only when task gives exact wording or diff.
- User-named tiering or model names override these defaults exactly. Use only models the harness lists as approved; if one unavailable, stop and say so, never substitute.
- Tier's agent carries its model and effort (§4). User-named tiering → spawn agent of the tier the mapping names. Model no agent carries: Claude Code → pass Agent call's `model` (alias) and `effort`; oh-my-pi → change role in `modelRoles`. Neither works → stop and say so.
- Reviewers not tiered: always on `dl-reviewer`'s model (§4; `implement-review-fix-loop` §3).

### Escalation ladder

Light → Standard → Deep, one step at a time; never skip a step, never move down mid-item. **Current tier**: tier of agent that last worked on item (after reuse, the session's tier, not item's class). Every step up starts from current tier and goes to a fresh agent, never back to the session that held the item. Four triggers move an item up:

1. **Agent struggles** (§5 separates struggling from asking). Stops editing, sends parent a **struggle handoff** (template in agent's system prompt, §4); parent re-assigns one step up at once (§5).
2. **Fix fails twice** at item's current tier. Failure: round check or full gate red on item's files after its agent reported done; re-review reports a prior finding on the item unresolved; fix introduced a regression. `VERDICT: FIX` carrying only new findings is not a failure. Count failures per work item, not per unit: a unit's verdict is not an item's count. After second failure next attempt goes one step up; never a third try at same tier.
3. **Reviewer upgrades the fixer.** Review finds many problems in developer's code → reviewer's `TIER: up` line sends next round's findings needing the unit's reasoning (later-rounds bullet above) to a fresh fixer one step above the tier that wrote the reviewed code, or at findings' own tier if higher. Orchestrator applies it unless its triage rejected the findings the reason rests on, and records that (`implement-review-fix-loop` §2 step 4).
4. **Parent's call.** Parent MAY move item up on own judgement when it sees item exceeds current tier (§5), without waiting for a report.

Deep has no step above. Any trigger at Deep (struggle handoff, second failed fix, reviewer `TIER: up`) → parent takes item over itself, working as in loop's takeover round (no subagents: verify, fix, targeted tests, round check; `implement-review-fix-loop` §2), or asks user; unit's other items and its round count continue unchanged. Record every escalation and its trigger for the report.

## 3. Partition by file, one owner per file

- Every file has exactly one task allowed to edit it. List owned files in task; forbid touching others.
- Docs several items touch (README, AGENTS.md) belong to **one docs task or the parent**, never to code tasks. Code tasks *report the wording* they need instead of editing the doc.
- Item forcing a minimal edit in another task's file (e.g. new struct field at a call site): allow explicitly, require agent to report it.
- Unify items sharing a mechanism into one task (e.g. two fixes in one module that must not be designed separately).
- Runners (tests, gate, deploy) own no files.

## 4. Spawn the tier's agent with a self-contained task

Every tier has a plugin agent (`agents/` in this plugin). Its system prompt carries what every task needs: absolute paths, owned files only, targeted tests only (never full suite or gate), no commit, shared docs reported not edited, regression tests proven to fail first, reviewer probes used as repro then deleted, the ask rule, struggle handoff template, report formats.

|Work|Agent|Model:effort|
|---|---|---|
|Light item|`dl-implementer-light`|`haiku-5-5:high`|
|Standard item|`dl-implementer-standard`|`sonnet-5-5:high`|
|Deep item|`dl-implementer-deep`|`opus-5-5:medium`|
|Tests, gate, deployment|`dl-runner`|`haiku-5-5:high`|
|Review (`implement-review-fix-loop` §3)|`dl-reviewer`|`opus-5-5:high`|

Spawn agent for item's tier; escalation (§2) spawns next one up. Task prompt carries only the item. Model routing per harness:

- **Claude Code**: reads `model` and `effort` from agent file; plugin agents named `develop-loop:<agent>` (e.g. `develop-loop:dl-runner`).
- **oh-my-pi**: ignores `model` in Claude-format plugin agents; route agents through model roles (`task.agentModelOverrides` → `modelRoles`) in `~/.omp/agent/config.yml` (global) or `.omp/config.yml` (project). Before first spawn read both, confirm all five `dl-*` agents routed. If one missing, entries to add: one `modelRoles` entry per agent-table row (`dl_light`, `dl_standard`, `dl_deep`, `dl_review`, each `<provider>/<model>:<effort>`) plus `task.agentModelOverrides` mapping each agent to its role as `"@<role>"` (`dl-runner` → `@dl_light`); repository README has it written out. Not routed → ask user **once** with two options: (a) add routing and continue tiered, or (b) run this session untiered, every agent on parent's model. Never fall back silently. Under (b): classification, ownership, reports still apply; ladder has no steps (struggle handoff or second failed fix goes straight to parent, as at Deep); report states tiers not applied. Tool limits (`disallowedTools`) also do not apply in oh-my-pi: `dl-reviewer` and `dl-runner` keep their limits by their prompts. Set thinking level in one place: never pass task tool's `effort` when agent's role or a per-call `model` already carries a `:level`; `effort` overrides it, and `hi` means model's highest level.
- **Harness without plugin agents**: paste agent file's body at top of task prompt; set model and effort with harness's own option.
- **Agent fails to resolve** mid-session (e.g. plugin updated under a running harness): spawn as in previous bullet, body pasted, model and effort from agent table; never fall back to harness's generic agent on its default model. After every spawn, compare the model and effort the agent resolved to (spawn status or session record) with agent table.

**New work:**

```
# Target
Worktree `<absolute path>`. Spec: <decision/doc ids>. Files you may edit: <list>. Environment: <can build and run tests | cannot: report breaks>.
Repo rules: <absolute path of the rules file>.
Other owners (do not touch): <list>. Non-goals: <list>.
Design: <wording given | design given | design open within constraints>.
# Change
1. <numbered steps; binding decisions inline; symbol/line hints; the constraints that make it correct>
# Tests
- <behaviour per rule; each side of every new guard; at least one regression test that fails before the change>
# Acceptance
<observable result>. Code, tests and docs in the working tree, uncommitted.
```

Constraints making a change correct go in `# Change`, verbatim ("refused attempts must not count toward the throttle", "Claude-Code-shaped bodies must pass byte for byte").

**Fix to a live session.** Fix goes back to the live implementer session owning its files (keeps context) only when all hold: session's tier equals fix's tier (§2); fix is in code that session wrote; no escalation trigger (§2) applies to item; session's context still small (under about 100k tokens). Otherwise spawn fresh agent at fix's own tier or, when a trigger applies, at tier §2 sets. Fresh fixer gets Target lines below; reused session gets only the round. Harness cannot message a running or idle subagent → spawn fresh one same way.

```
# Target (fresh fixer only)
Worktree `<absolute path>`. Files you may edit: <list, including the `dl-probe` files below>. Environment: <can build and run tests | cannot: report breaks>. Diff so far:
`git -C <worktree> diff <base>`. Previous report: <attached>.
Repo rules: <absolute path of the rules file>.
# Round
Round <N> findings on your files: <n> critical, <n> major, <n> minor.
Binding decisions:
- <finding id>: <decision, with evidence>
Probes (reviewer repros; reproduce with each, fix, carry the case into the regression test, then delete it):
- <finding id>: `<path>` · run: `<command>`
Tests: targeted only (your new tests and the existing tests of the code you change); never the full suite.
```

Diff includes new files because loop's orchestrator ran `add -N` before review (`implement-review-fix-loop` §2 steps 2 and 6).

**Runner:**

```
Run, in order, from <cwd>: <exact commands>.
```

## 5. Answering questions and obstacles

Every subagent spawned under this skill asks instead of guessing. Typical triggers: task ambiguous, two designs plausible, edit needed outside owned files, tool or environment fails, task contradicts a contract document. Missing fact, decision or permission → **question**. Agent with everything it needs but unable to get the work right (test it cannot get passing, reasoning it is unsure of, work beyond what it can do reliably) → **struggling**; sends struggle handoff instead (§2).

Parent answers promptly (waiting agent = spend without progress) with one of:

- **binding decision**, recorded with the task so later rounds and re-spawns see it;
- **re-assignment** on struggle handoff: spawn agent one tier up the ladder (§2) with original task, the handoff, and "continue from the working tree; restart only parts the handoff marks broken". Struggling agent stays stopped. If handoff shows struggle was really a missing decision, decide it and keep same agent instead.
- **ownership**: route edit to file's owner, or widen this task's files when no other task owns them;
- **escalation** to next tier (§2 trigger 4) when parent sees item exceeds current one, without waiting for agent to report it;
- **the user**, for operator decisions (contract change, new dependency, security or durability trade-off); tell agent which parts to continue meanwhile.

Two questions on one item showing design never decided → stop item, decide it first in orchestrator's triage. Deviation in a report never asked about = guess: treat as finding, send back.

## 6. Spawn once, batch, then integrate

Spawn all independent tasks in a **single message** (one block of parallel task calls). Do not poll; answer questions (§5) and do productive work while they run. Only edit parent makes meanwhile: apply doc wording agents report, serialized after docs task finishes (editing a doc while its owner still runs clobbers lines).

Verify doc edits by reading the result.

## 7. Round check and full gate

Implementers and fixers never run full test suite or gate; where environment allows they format and compile-check own files and run targeted tests only (their new tests + existing tests of code they change). After every task of the batch (§6) returns, loop's orchestrator runs **round check** once per batch (never per task): format, lint, build, no test suite. **Full gate** in repo's documented order (format, lint, build, full test suite, other checks, duplicate/clone detection) runs once, after every unit passed all its review rounds (`implement-review-fix-loop` §7 step 1). Orchestrator runs both itself or through `dl-runner`, reading and judging its raw output. Expect and handle:

1. **Duplicate-code / clone detectors** flag near-identical test setups parallel agents write independently. Dispatch as fix items (Standard tier): extract one helper per pair, never weaken assertions. Fixer MAY run duplicate detector itself (static tool, not a build) and reports its output. Like every fix: loop's round check and re-review, then full gate again, before landing.
2. **Mechanical diagnostics**: strict-lint noise on helpers added for tests (e.g. redundant visibility), compile error at a named line, format diff. Tool prints exact fix → parent applies it as printed (exceptions at top of `implement-review-fix-loop`); otherwise dispatch as fix items (Light tier).
3. **New cap/guard breaks old concurrency test.** New bound changes observable mix of outcomes (e.g. some attempts now get 503) → dispatch fix item (Standard tier: test of decided concurrency behaviour, §2) adapting test to invariants still holding (checked ≤ limit, counted == checked, outcomes sum to total). Say so in report; do not silently loosen a test exercising a valid case without stating why old expectation no longer applies.
4. Any edit after full gate invalidates it: re-run after the last one. Fixes for its failures run targeted tests only, like every fix; only orchestrator runs full gate.

## 8. Report to the loop

Per item: done (implemented / fixed / documented / run) or not done, choice made, tier it ran at, any escalation with trigger (struggle handoff, second failed fix, reviewer `TIER: up`, parent's call). Then:

- questions agents asked and answers given, when they changed the design
- anything unexercised (not run live, behaviour only structurally testable)
- decisions left open to user (e.g. "misleading message kept; want a distinct one?")
- one line per agent: tier, requests, cost and context size where harness reports them, escalations and rework, so defaults can be tuned

## Pitfalls seen

- Agents told not to build or run tests cannot catch own breakage: budget a fix round.
- Two agents sharing a test module both add helpers → duplicates; assign test regions.
- Reviewer's "fix" option contradicting contract doc (README) loses; doc authoritative, so deliberately fix whichever side the doc says is wrong.
- Don't spawn more agents than real file-disjoint slices.
- Agent guessing instead of asking produces plausible code contradicting the contract; ask rule lives in every agent's system prompt (or pasted body), never assumed.
- Re-prompting a Light agent on work needing reasoning burns rounds; escalate instead.
- Agent hiding a struggle (patching until a test passes by accident) costs more than the upgrade; handoff is the expected path, and agent's prompt says so.
- Replacing a line range with fewer lines than the range silently eats neighbouring text; re-read region after each range edit.
