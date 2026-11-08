---
name: triage-findings
description: Use when there is a pile of findings (a review report, a backlog file, scanner or scout output, a minor sweep list) and the user asks what is worth fixing, or says "fix the ones worth fixing". Verifies each finding, scores value against cost and risk with explicit criteria, and returns a decision per finding (fix now, quick sweep, defer, reject, needs a decision) with reasons. The findings source is given after the command, for example /review-loop:triage-findings backlog.md. Not for writing the fixes themselves.
argument-hint: 'source of findings: a file path, "last review", or pasted text; optionally a bar such as "security only"'
---

# Triage: $ARGUMENTS

**Source (and optional bar):** $ARGUMENTS

If that line is empty or still shows the placeholder, use, in order: the most recent review
output in this conversation, then `backlog.md` at the repository root; if neither exists,
ask where the findings are.

Triage turns a list into decisions. Its output is a table the user can approve in one
read; it does not change code. Fixes are handed to `review-fix-fanout` (model-tiered,
one owner per file) or `implement-review-fix-loop` (when the work needs review rounds).

## 1. Verify before judging

A finding is a claim. Check each one against the current tree before deciding anything:

- **Still holds?** Open the cited `file:line`; reproduce or trace it. Findings go stale
  when later commits change the code.
- **Evidence?** A finding with no code citation or no failure path is unverified,
  not rejected: downgrade it and say what would verify it.
- **Weak-source rule:** findings from small models, scouts and scanners are leads, not
  facts. Verify every one of them independently; do not sample.
- **Duplicates:** merge findings that share a root cause; keep one row, list the
  copies. The same finding repeated across review rounds is one item.
- **Re-rate severity from the evidence**, not from the reporter's label.

## 2. Gather the context that overrides your defaults

Before applying the criteria, read what the project already decided:

- repo rules (`AGENTS.md`/`CLAUDE.md` and equivalents): *must-fix classes* (for example
  "performance findings are must-fix", "stale contract docs are major"), forbidden fixes,
  required tests;
- the decision records/design docs: a finding that contradicts a written decision is a
  *needs-decision* item, not an automatic fix (the decision may be wrong; that is the
  user's call);
- approved designs and mockups: a fix that departs from them needs approval first.

Project rules beat the generic criteria below.

## 3. Criteria

Rate each verified finding on these axes:

| Axis | Question |
|---|---|
| Impact | What breaks or degrades: security, data loss, correctness, user-visible behaviour, a contract (docs, schema, API), performance, maintainability, cosmetics? |
| Reachability | Can untrusted input or a default configuration reach it? Does it occur on a hot or common path, or only in a contrived state? |
| Confidence | Verified by reproduction (high), by code trace (medium), by reporter's word only (low) |
| Scope | Is it on lines this change added or altered, a regression the change caused, or pre-existing? |
| Fix cost | Lines and files touched, tests needed, time |
| Fix risk | Can the fix itself break behaviour, a public contract, a wire format, a schema, an accepted design? |

### Gates (first match decides)

1. Does not hold, already fixed, or not a defect -> **Reject** (state which).
2. Contradicts a recorded decision or approved design, or the only fix would change
   *behaviour* that a contract promises (public API, wire format, schema, a documented
   guarantee) -> **Needs decision** (ask; see §5). Documentation that fell behind the code
   is not this gate: see gate 5.
3. Security hole, data loss, or correctness failure reachable by real input or default
   config -> **Fix now**, regardless of cost.
4. Regression introduced by the current change -> **Fix now**.
5. Requirement or acceptance criterion unmet; observable behaviour with no test; a stale
   *contract document* (API docs, schema/migration notes, another unit's spec) -> **Fix now**.
   When a document and the code disagree, the document that states the intended contract
   decides which side is wrong; if it is genuinely ambiguous, take the conservative side (the
   one that does not change behaviour), apply it, and say so in the table.
6. A project must-fix class (§2) -> **Fix now**.

### Value versus cost (everything left)

| | Low fix cost and risk | High fix cost or risk |
|---|---|---|
| **High value** (real, reachable, likely to matter) | **Fix now** | **Fix now** as its own unit with its own review and tests |
| **Low value** (cosmetic, unlikely, contrived) | **Quick sweep** if the file is being touched anyway, else **Defer** | **Reject**, or **Defer** with a revisit trigger |

Additional rules:

- **Pre-existing and out of scope** -> **Defer** to the backlog with a trigger ("when
  this module is next changed"), never a vague "later".
- **Taste** that a formatter or linter would decide -> **Reject**. Style the project has
  no rule for is a **Reject** unless it causes defects.
- **Performance**: fix if measured, or unbounded on the worst legal input, or on a hot
  path the rules protect. Otherwise **Defer/Reject** unless it is a must-fix class (§2).
  A micro-optimisation with no measurement is a guess.
- **Duplication**: judged by whether the code does the *same job*. Extract when the
  behaviour is the same; **Reject** merges of code that happens to look alike but serves
  different purposes or would need a flag to tell them apart.
- **The fix is worse than the problem** (adds a layer, an abstraction or a dependency for
  a minor gain; breaks an accepted design) -> **Reject** or **Needs decision**.
- **Missing tests** for observable behaviour are a *fix* (they are the evidence); a
  missing test for wiring, a copy or a default is a **Reject**.
- **Several minors in one file** can be one sweep; do not file each as its own unit.
- **Nothing is rejected silently.** Every reject gets a one-line reason a reviewer
  could not re-raise unchanged.

## 4. Output

One table, ordered Fix now -> Needs decision -> Quick sweep -> Defer -> Reject:

```
| # | Finding (source id) | Verified | Sev (re-rated) | Decision | Reason | Cost | Hand-off |
```

- `Verified`: yes (how: repro / trace) / no (what would verify).
- `Hand-off` for fixes: owning file(s) and suggested model tier (docs and mechanical
  -> cheapest; pattern-following -> mid; design or cross-cutting -> strongest).
- `Defer` rows carry the trigger; `Reject` rows carry the reason.
- Then counts per decision, and the **residual risk** of everything not fixed in one
  sentence each for anything that is security, data or correctness related.

Write deferred items to `backlog.md` at the repo root (excluded from git through
`.git/info/exclude`, never committed) with where, what, and the trigger.

## 5. Needs-decision items: ask, with a recommendation

Batch every needs-decision item into one question to the user. Each has 2-4 concrete
options with the trade-off, and a recommended one. Typical triggers: finding versus
recorded decision, fix departs from approved design, security versus compatibility,
large cost for moderate value. Do not start fixing them in the meantime.

## 6. Hand-off and the loop

After the user approves the table:

- *Fix now* and *Quick sweep* -> `review-fix-fanout` (partition by file, tier by model) or
  `implement-review-fix-loop` when review rounds are needed;
- re-triage only what the fix introduced; do not reopen rejected items unless the
  reporter shows why the reason is wrong;
- keep the table: it is the record of what was decided and why.

## Pitfalls seen

- Treating a scout's or scanner's list as fact: some entries were wrong, some stale.
- "Fix everything" on a minor-heavy list: minors beget new drift each round; sweep the
  cheap ones, defer or reject the rest.
- Rejecting a finding without a reason, so the next review re-raises it.
- Letting an agent fix a finding that contradicts a written decision.
- Counting duplicates as separate findings and overstating the backlog.
