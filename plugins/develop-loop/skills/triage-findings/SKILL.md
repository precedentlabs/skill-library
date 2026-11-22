---
name: triage-findings
description: Use when there is a pile of findings (a review report, a backlog file, scanner or scout output, a minor sweep list) and the user asks what is worth fixing, what to fix next, or says "fix the ones worth fixing". Verifies each finding, scores value against cost and risk with explicit criteria, returns a decision per finding (fix now, quick sweep, defer, reject, needs a decision) with reasons, and selects the next batch to hand to implement-review-fix-loop. The findings source is given after the command, for example /develop-loop:triage-findings backlog.md. Not for writing the fixes themselves.
argument-hint: 'source of findings: a file path, "last review", or pasted text; optionally a bar such as "security only"'
---

# Triage: $ARGUMENTS

**Source (and optional bar):** $ARGUMENTS

If that line is empty or still shows the placeholder → use args given after skill name (oh-my-pi appends them as trailing `User:` line). No args → use, in order: most recent review output in this conversation, then `backlog.md` at main checkout root; neither exists → ask where findings are.

Triage turns a list into decisions and picks next batch. Output: table user can approve in one read. Changes no code. Top of hierarchy: batch → `implement-review-fix-loop`, which implements and reviews it, running work through `tiered-fanout` (model tier per difficulty, one owner per file).

## 1. Verify before judging

Finding = claim. Check each against current tree before deciding anything:

- **Still holds?** Open cited `file:line`; reproduce or trace. Later commits changing code make findings stale.
- **Evidence?** No code citation or no failure path → unverified, not rejected: downgrade it, state what would verify it.
- **Weak-source rule:** findings from small models, scouts, scanners: leads, not facts. Verify every one independently; do not sample.
- **Duplicates:** merge findings sharing a root cause; one row, list copies. Same finding repeated across review rounds = one item.
- **Re-rate severity from evidence**, not reporter's label.

## 2. Gather the context that overrides your defaults

Before applying criteria, read what project already decided:

- repo rules (`AGENTS.md`/`CLAUDE.md` and equivalents): *must-fix classes* (e.g. "performance findings are must-fix", "stale contract docs are major"), forbidden fixes, required tests;
- decision records/design docs: finding contradicting a written decision → *needs-decision* item, not automatic fix (decision may be wrong; user's call);
- approved designs, mockups: fix departing from them needs approval first.

Project rules beat generic criteria below.

## 3. Criteria

Rate each verified finding on:

|Axis|Question|
|---|---|
|Impact|What breaks or degrades: security, data loss, correctness, user-visible behaviour, contract (docs, schema, API), performance, maintainability, cosmetics?|
|Reachability|Reachable by untrusted input or default config? Hot/common path, or only contrived state?|
|Confidence|Reproduced (high), code trace (medium), reporter's word only (low)|
|Scope|On lines this change added/altered, regression or exposure this change caused, or pre-existing?|
|Fix cost|Lines and files touched, tests needed, time|
|Fix risk|Can fix itself break behaviour, public contract, wire format, schema, accepted design?|

### Gates (first match decides)

1. Does not hold, already fixed, or not a defect → **Reject** (state which).
2. Contradicts recorded decision or approved design, or only fix would change *behaviour* a contract promises (public API, wire format, schema, documented guarantee) → **Needs decision** (ask; see §5). Docs that fell behind code: not this gate; see gate 5.
3. Security hole, data loss, or correctness failure reachable by real input or default config → **Fix now**, regardless of cost.
4. Regression introduced by current change → **Fix now**.
5. Requirement or acceptance criterion unmet; observable behaviour with no test; stale *contract document* (API docs, schema/migration notes, another unit's spec) → **Fix now**. Doc and code disagree → document stating intended contract decides which side is wrong; genuinely ambiguous → take conservative side (one not changing behaviour), apply it, say so in table.
6. Project must-fix class (§2) → **Fix now**.

### Value versus cost (everything left)

||Low fix cost and risk|High fix cost or risk|
|---|---|---|
|**High value** (real, reachable, likely to matter)|**Fix now**|**Fix now** as own unit with own review and tests|
|**Low value** (cosmetic, unlikely, contrived)|**Quick sweep** if file touched anyway, else **Defer**|**Reject**, or **Defer** with revisit trigger|

Additional rules:

- **Pre-existing and out of scope** → **Defer** to backlog with trigger ("when this module is next changed"), never vague "later".
- **Taste** a formatter or linter would decide → **Reject**. Style with no project rule → **Reject** unless it causes defects.
- **Performance**: fix if measured, or unbounded on worst legal input, or on hot path the rules protect. Otherwise **Defer/Reject** unless must-fix class (§2). Unmeasured micro-optimisation = guess.
- **Duplication**: judged by whether code does the *same job*. Same behaviour → extract. **Reject** merging code that merely looks alike but serves different purposes or would need a flag to distinguish.
- **Fix worse than problem** (adds layer, abstraction, or dependency for minor gain; breaks accepted design) → **Reject** or **Needs decision**.
- **Missing tests** for observable behaviour → *fix* (they are the evidence); missing test for wiring, a copy, or a default → **Reject**.
- **Several minors in one file** can be one sweep; do not file each as own unit.
- **Nothing rejected silently.** Every reject gets one-line reason a reviewer could not re-raise unchanged.

## 4. Output

One table, ordered Fix now → Needs decision → Quick sweep → Defer → Reject:

```
| # | Finding (source id) | Verified | Sev (re-rated) | Decision | Reason | Cost | Hand-off |
```

- `Verified`: yes (how: repro / trace) / no (what would verify).
- `Hand-off` for fixes: owning file(s) + difficulty class (Light / Standard / Deep, per `tiered-fanout` §2); loop passes it on as tier hint.
- `Defer` rows carry trigger; `Reject` rows carry reason.
- Then counts per decision, plus **residual risk** of everything not fixed: one sentence each for anything security-, data-, or correctness-related.

Write deferred items (where, what, trigger) to `backlog.md` at main checkout root (excluded from git via `.git/info/exclude`, never committed).

## 5. Needs-decision items: ask, with a recommendation

Batch all needs-decision items into one question to user. Each: 2-4 concrete options with trade-off, plus a recommended one. Typical triggers: finding vs recorded decision, fix departs from approved design, security vs compatibility, large cost for moderate value. Do not start fixing them meanwhile.

## 6. Select the next batch

From approved *Fix now* and *Quick sweep* rows, pick what next loop run takes:

1. **Order** by deciding gate (security/data/correctness → regression → unmet requirement or stale contract → project must-fix class → value-versus-cost), then re-rated severity, then cheaper first.
2. **Group** rows sharing owning file or root cause; group goes in whole or not at all. *Quick sweep* rows ride with the group owning their file; rows whose file has no *Fix now* group left form one sweep group of their own (counts toward cap).
3. **Cap** batch at user's limit, else 5 file-disjoint groups. High-cost or high-risk *Fix now* row = batch of its own.
4. **Hold back** rows waiting on a *Needs decision* answer or on another row's fix.

Rows left out stay in table as `queued` with their order; table, not memory, is the queue.

## 7. Hand-off and the loop

After user approves table and batch (request already asking to fix, e.g. "triage and fix" or "fix the ones worth fixing", approves Fix now and Quick sweep rows; ask only Needs decision items, §5):

- batch → `implement-review-fix-loop` with loop's stop bar: severity bar user named for the loop, else its default (no critical, major, or minor). Selection bar given to triage (e.g. "security only") only filters rows here; never passed to loop. Nothing handed straight to fixers ⇒ every fix gets review;
- when loop ends, triage only what is new (its backlog entries and out-of-scope findings, plus anything fixes introduced), merge into queue, select next batch. Show new rows and next batch for approval; rows already approved and queued need no second approval. Stop when queue empty or user stops;
- do not reopen rejected items unless reporter shows why reason is wrong;
- keep the table: record of what was decided and why.

## Pitfalls seen

- Treating scout's or scanner's list as fact: some entries wrong, some stale.
- "Fix everything" on minor-heavy list: minors beget new drift each round; sweep cheap ones, defer or reject rest.
- Rejecting without reason ⇒ next review re-raises it.
- Letting an agent fix a finding contradicting a written decision.
- Counting duplicates as separate findings, overstating backlog.
