---
name: tiered-fanout
description: Use when implement-review-fix-loop dispatches implement or fix work to parallel subagents, each on the cheapest model tier adequate for its difficulty, or when tests, the gate or a deployment should be run by a cheap runner. Not for code or doc changes outside the develop loop, deciding what to fix (triage-findings), or reviewing.
---

# Tiered fanout: develop or fix with model-tiered subagents

Run decided work through parallel subagents without file collisions, wasted model spend,
silent guessing, or a gate that fails at the end.

Place in the hierarchy: `triage-findings` selects a batch → `implement-review-fix-loop`
implements, reviews and fixes it → this skill does the implement and fix work. It calls
nothing above it.

- **Inside the loop** (all implementation work): subagents never commit; the loop's
  per-round triage supplies the decisions (§1), the loop runs the gate (§7 lists the
  fallout to expect), and §8 feeds the loop's report.
- **Standalone: runs only.** Without the loop, use it only for runner tasks that change no
  files (tests, the gate, deployments). Any code or doc change, even a one-line fix, goes
  through `implement-review-fix-loop`.

## 1. Inputs: decided work items

A work item is a development unit (spec + binding decisions), a fix (finding + the
decision taken on it), or an operational run (tests, gate, deployment). Every item arrives
decided: no open design question goes to a subagent. For development units and fixes the
loop's orchestrator decides; for a standalone run, the exact commands are the decision.

When a finding is a contract mismatch with two valid resolutions (fix the code vs. fix the
docs), pick the conservative one, state it in the task, and say so in the report.

## 2. Classify difficulty → model tier

| Tier | Work |
|---|---|
| Light | docs and comment wording, doc table rows, simple tests in an existing harness, mechanical edits (renames, config entries, boilerplate from a given template), running tests or the gate and reporting raw output, deployments the user asked for |
| Standard | small to medium coding work: a handler, endpoint or feature following an existing pattern, rewriting one function, non-trivial tests, bounding a resource with an existing primitive; no complicated algorithms |
| Deep | multi-module work, concurrency and lifecycle, complex algorithms, optimisations, startup/migration ordering, wire-format and security invariants, refactoring a shared primitive, fixes with two plausible directions, any large task that needs complex reasoning |

- Classify per item, not per batch. An item merged from several (§3) takes the highest
  tier of its parts.
- **Up one tier** when the item touches another module's contract, concurrency,
  persistence or security, has no existing pattern to copy, or its design is open within
  constraints.
- **Down one tier** only when the task gives the exact wording or diff.
- User-named tiering or model names override these defaults exactly. Use only models the
  harness lists as approved; if one is unavailable, stop and say so, never substitute.
- The tier's agent carries its model and effort (§4). To follow a user-named tiering,
  spawn the agent of the tier the mapping names. For a model no agent carries: in Claude
  Code pass the Agent call's `model` (alias) and `effort`; in oh-my-pi change the role in
  `modelRoles`. If neither works, stop and say so.
- Reviewers are not tiered: they always run on `dl-reviewer`'s model (§4;
  `implement-review-fix-loop` §3).

### Escalation ladder

Light → Standard → Deep, one step at a time; never skip a step and never move down
mid-item. An item's **current tier** is the tier of the agent that last worked on it
(after a reuse, the session's tier, not the item's class); every step up starts from there
and goes to a fresh agent, never back to the session that held the item. Four triggers
move an item up:

1. **The agent struggles** (§5 draws the line between struggling and asking). It stops
   editing and sends the parent a **struggle handoff** (template in the agent's system
   prompt, §4); the parent re-assigns the item one step up at once (§5).
2. **A fix fails twice** at the item's current tier. A failure is one of: the gate is red
   on the item's files after its agent reported done; the re-review reports a prior
   finding on the item unresolved; the fix introduced a regression. A `VERDICT: FIX` that
   only carries new findings is not a failure. Failures are counted per work item, not per
   unit: a unit's verdict is not an item's count. After the second failure the next
   attempt goes one step up; never a third try at the same tier.
3. **The reviewer upgrades the fixer.** When a review finds many problems in the
   developer's code, the reviewer's `TIER: up` line sends the unit's next fix round to a
   fresh fixer one step above the tier that wrote the reviewed code, or at the findings'
   own tier if that is higher. The orchestrator applies it unless its triage rejected the
   findings the reason rests on, and records that (`implement-review-fix-loop` §2 step 4).
4. **The parent's call.** The parent may move an item up on its own judgement when it sees
   the item exceeds the current tier (§5), without waiting for a report.

Deep has no step above. On any trigger at Deep (struggle handoff, second failed fix,
reviewer `TIER: up`) the parent takes the item over itself, working as in the loop's
takeover round (no subagents: verify, fix, gate; `implement-review-fix-loop` §2), or asks
the user; the unit's other items and its round count go on unchanged. Record every
escalation and its trigger for the report.

## 3. Partition by file, one owner per file

- Every file has exactly one task that may edit it. List owned files in the task and
  forbid touching others.
- Docs that several items touch (README, AGENTS.md) belong to **one docs task or the
  parent**, never to the code tasks. Code tasks *report the wording* they need instead of
  editing the doc.
- If an item forces a minimal edit in another task's file (e.g. a new struct field at a
  call site), allow it explicitly and require the agent to report it.
- Unify items that share a mechanism into one task (e.g. two fixes in one module that must
  not be designed separately).
- Runners (tests, gate, deploy) own no files.

## 4. Spawn the tier's agent with a self-contained task

Every tier has a plugin agent (`agents/` in this plugin). Its system prompt carries what
every task needs: absolute paths, owned files only, no gate, no commit, shared docs
reported instead of edited, regression tests proven to fail first, the ask rule, the
struggle handoff template and the report formats.

| Work | Agent | Model:effort |
|---|---|---|
| Light item | `dl-implementer-light` | `haiku-5-5:high` |
| Standard item | `dl-implementer-standard` | `sonnet-5-5:high` |
| Deep item | `dl-implementer-deep` | `opus-5-5:medium` |
| Tests, gate, deployment | `dl-runner` | `haiku-5-5:high` |
| Review (the loop's §3) | `dl-reviewer` | `opus-5-5:high` |

Spawn the agent for the item's tier; an escalation (§2) spawns the next one up. The task
prompt carries only the item. Model routing per harness:

- **Claude Code** reads `model` and `effort` from the agent file; plugin agents are named
  `develop-loop:<agent>` there (e.g. `develop-loop:dl-runner`).
- **oh-my-pi** ignores `model` in Claude-format plugin agents; route the agents through
  model roles (`task.agentModelOverrides` → `modelRoles`) in `~/.omp/agent/config.yml`
  (global) or `.omp/config.yml` (project). Before the first spawn read both and confirm
  that all five `dl-*` agents are routed. If one is missing, the entries to add are one
  `modelRoles` entry per row of the agent table (`dl_light`, `dl_standard`, `dl_deep`,
  `dl_review`, each `<provider>/<model>:<effort>`) and `task.agentModelOverrides` mapping
  each agent to its role as `"@<role>"` (`dl-runner` → `@dl_light`); the repository README
  has it written out. If they are not routed, ask the user **once** with two options:
  (a) add the routing and continue tiered, or (b) run this session untiered, every agent
  on the parent's model. Never fall back silently. Under (b) classification, ownership and
  reports still apply, the ladder has no steps (a struggle handoff or a second failed fix
  goes straight to the parent, as at Deep), and the report states that tiers were not
  applied. Tool limits (`disallowedTools`) do not apply in oh-my-pi either: `dl-reviewer`
  and `dl-runner` stay read-only by their prompts.
- **A harness without plugin agents**: paste the agent file's body at the top of the task
  prompt and set model and effort with the harness's own option.

**New work:**

```
# Target
Worktree `<absolute path>`. Spec: <decision/doc ids>. Files you may edit: <list>.
Repo rules: <absolute path of the rules file>.
Other owners (do not touch): <list>. Non-goals: <list>.
Design: <wording given | design given | design open within constraints>.
# Change
1. <numbered steps; binding decisions inline; symbol/line hints; the constraints that make it correct>
# Tests
- <behaviour per rule; at least one regression test that fails before the change>
# Acceptance
<observable result>. Code, tests and docs in the working tree, uncommitted.
```

Constraints that make a change correct belong in `# Change`, verbatim ("refused attempts
must not count toward the throttle", "Claude-Code-shaped bodies must pass byte for byte").

**Fix to a live session.** A fix whose files belong to a live implementer session goes
back to that session (it keeps context) when that session's tier is at or above the fix's
tier and no escalation trigger (§2) applies to the item. Otherwise spawn a fresh agent at
the fix's tier or, when a trigger applies, at the tier §2 sets. A fresh fixer gets the
Target lines below; a reused session gets only the round. If the harness cannot message a
running or idle subagent, spawn a fresh one the same way.

```
# Target (fresh fixer only)
Worktree `<absolute path>`. Files you may edit: <list>. Diff so far:
`git -C <worktree> diff <base>`. Previous report: <attached>.
Repo rules: <absolute path of the rules file>.
# Round
Round <N> findings on your files: <n> critical, <n> major, <n> minor.
Binding decisions:
- <finding id>: <decision, with evidence>
```

The diff includes new files because the loop's orchestrator ran `add -N` before the review
(`implement-review-fix-loop` §2 steps 2 and 6).

**Runner:**

```
Run, in order, from <cwd>: <exact commands>.
```

## 5. Answering questions and obstacles

Every subagent spawned under this skill asks instead of guessing. Typical triggers: the
task is ambiguous, two designs are plausible, an edit is needed outside the owned files, a
tool or the environment fails, the task contradicts a contract document. A missing fact,
decision or permission is a **question**. An agent that has everything it needs but cannot
get the work right (a test it cannot get passing, reasoning it is not sure of, work beyond
what it can do reliably) is **struggling** and sends a struggle handoff instead (§2).

The parent answers promptly (a waiting agent is spend with no progress) with one of:

- a **binding decision**, recorded with the task so later rounds and re-spawns see it;
- **re-assignment** on a struggle handoff: spawn the next model up the ladder (§2) with
  the original task, the handoff and "continue from the working tree; restart only parts
  the handoff marks broken". The struggling agent stays stopped. If the handoff shows the
  struggle was really a missing decision, decide it and keep the same agent instead.
- **ownership**: route the edit to the file's owner, or widen this task's files when no
  other task owns them;
- **escalation** to the next tier (§2 trigger 4) when the parent sees the item exceeds the
  current one, without waiting for the agent to report it;
- **the user**, for operator decisions (contract change, new dependency, security or
  durability trade-off); tell the agent which parts to continue meanwhile.

Two questions on one item that show the design was never decided → stop the item and
decide it first in the orchestrator's triage. A deviation in a report that was never asked
about is a guess: treat it as a finding and send it back.

## 6. Spawn once, batch, then integrate

Spawn all independent tasks in a **single message** (one block of parallel task calls).
Do not poll; answer questions (§5) and do productive work while they run. The one edit the
parent makes meanwhile: apply the doc wording agents report, serialized after the docs
task finishes (editing a doc while its owner is still running clobbers lines).

Verify doc edits by reading the result.

## 7. Gate fallout after a fanout

Implementers do not build. After every task of the batch (§6) is back, the loop's
orchestrator runs the project's full gate once per batch (never once per task), in the
repo's documented order (format, lint, tests, other checks, duplicate/clone detection),
itself or through `dl-runner`, whose raw output it reads and judges. Expect and handle:

1. **Duplicate-code / clone detectors** flag the near-identical test setups that parallel
   agents write independently. Dispatch them as fix items (Standard tier): extract one
   helper per pair, never weaken assertions. Like every fix, they get the loop's gate and
   re-review before they land.
2. **Strict-lint noise** on helpers added for tests (e.g. redundant visibility).
3. **A new cap/guard breaks an old concurrency test.** When a new bound changes the
   observable mix of outcomes (e.g. some attempts now get 503), adapt the test to the
   invariants that still hold (checked ≤ limit, counted == checked, outcomes sum to
   total). Say so in the report; do not silently loosen a test that exercises a valid case
   without stating why the old expectation no longer applies.
4. Re-run the full gate after the last edit; one edit invalidates it.

## 8. Report to the loop

Per item: done (implemented / fixed / documented / run) or not done, the choice made, the
tier it ran at and any escalation with its trigger (struggle handoff, second failed fix,
reviewer `TIER: up`, parent's call). Then:

- questions agents asked and the answers given, when they changed the design
- anything unexercised (not run live, behaviour only structurally testable)
- decisions left open to the user (e.g. "misleading message kept; want a distinct one?")
- one line per tier on how it did (escalations, rework), so the defaults can be tuned

## Pitfalls seen

- Agents asked not to build or run tests cannot catch their own breakage: budget a fix round.
- Two agents sharing a test module both add helpers → duplicates; assign test regions.
- A reviewer's "fix" option that contradicts the contract doc (README) loses; the doc is
  authoritative, so fix whichever side the doc says is wrong, deliberately.
- Don't spawn more agents than there are real file-disjoint slices.
- An agent that guesses instead of asking produces plausible code that contradicts the
  contract; the ask rule lives in every agent's system prompt (or the pasted body), never
  assumed.
- Re-prompting a Light agent on work that needed reasoning burns rounds; escalate instead.
- An agent that hides a struggle (keeps patching until a test passes by accident) costs
  more than the upgrade would; the handoff is the expected path and the agent's prompt
  says so.
- Replacing a line range with fewer lines than the range silently eats neighbouring text;
  re-read the region after each range edit.
