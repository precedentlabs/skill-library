---
name: implement-review-fix-loop
description: Use for all implementation work - any request to implement, change, fix, simplify or refactor code, tests or docs, a batch selected by triage-findings, or an accepted optimize change - and loop review → fix until no critical, major or minor finding is left ("repeat until clean", "until nothing blocks"). Covers an architecture map before code, unit partitioning, size budgets and simplify mode, severity definitions, the per-round protocol (implement and fix steps run through tiered-fanout), design rethinks proposed to the user, convergence and stop rules, scoping reviews to the diff and its blast radius, a backlog for out-of-scope findings, worktrees, and the final gate. Not for a one-shot review with no changes, or for deciding which findings to fix (triage-findings).
---

# Implement → review → fix, until clean

Orchestrator decides, gates, commits. Subagents implement, review, fix. Orchestrator edits a unit's files ONLY in these cases; never otherwise to apply a finding, however small:
- cosmetic tail and takeover round (§2);
- item `tiered-fanout` §2 hands to parent (trigger at Deep, or any trigger in untiered session, `tiered-fanout` §4);
- doc wording a subagent reported for a shared doc (`tiered-fanout` §3 and §6);
- round-check or gate diagnostic whose exact fix the tool prints (compile error at named line, lint with suggested replacement, format diff): few lines in one file, applied as printed, confirmed by re-running that check (`tiered-fanout` §7).

Nothing "done" on a subagent's word. Loop ends only on reviewer verdict (or cosmetic tail, §2) **plus** green full gate, test suite included, run by orchestrator once all review rounds passed (§7 step 1; run by itself, or by `dl-runner` whose raw output it reads and judges). Only other full gate: refactor unit's own, before feature units branch (§0).

### Who runs which tests

|Who|Runs|Never runs|
|---|---|---|
|Implementer, fixer|where environment allows: format and compile check of files it touched; **targeted tests only** (tests it adds + existing tests exercising code it changed, selected by file or filter), as often as needed; reviewer's probe of each finding it fixes|full test suite, gate|
|Reviewer|only its own throwaway `dl-probe` files (§3)|full test suite, project's tests, gate|
|Orchestrator (itself or via runner agent of `tiered-fanout` §4)|per round: **round check** (format, lint, build; no test suite) + size (§0) + targeted commands of §2 steps 4 and 6; **once, after every unit passed all its review rounds**: **full gate** (format, lint, build, full test suite, other checks; §7 step 1), again after any later edit; refactor unit (§0): its own full gate before feature units branch|full test suite during review rounds|

**Probe lifecycle.** Reviewer proves a finding with throwaway test or script (`dl-probe` file, §3) and keeps it; finding names its path, run command, result. Probe goes to that finding's fixer as repro case: fixer runs it to see failure, fixes, runs it to see pass, carries case into permanent regression test (extending an existing test or test table when one fits), deletes probe. Only that fixer deletes it. Two exceptions (probes with no fixer): reviewer deletes a probe that proved no finding before reporting; orchestrator deletes probe of a finding it rejects or accepts as is (§2 step 4). No `dl-probe` file ever committed.

Place in hierarchy: `triage-findings` selects batch → this loop → `tiered-fanout` does implement and fix work, each item on the model tier its difficulty needs. Loop never calls triage; out-of-scope findings reach it through backlog (§4).

**All implementation work goes through this loop**: features, fixes, triage batches, accepted `optimize` changes, doc and test changes. Small change runs same loop at smallest size (Loop size, §0), never a skipped review. Only runs changing no files (tests, gate, deployments) use `tiered-fanout` without it.

## 0. Pin the contract before any code

- Decisions spec left open: taken (or asked with 2–4 concrete options) and **written down first** (decision record / design doc, committed). Implementer never guesses them.
- Split work into **units**; units running in parallel have disjoint file sets (a unit waiting for another's commit may share its files). Order units by risk (security fixes before functional changes). One unit = one implement/review/fix loop.
- Code map unknown → one read-only scout first (harness built-in: Claude Code `Explore`, oh-my-pi `scout`); implementers read its briefing instead of exploring.
- **Architecture map**, only when spec or scout briefing suggests a redesign is probably necessary: no clear owner for feature's data, feature would duplicate or work around an existing mechanism, or change crosses module boundaries. No such signal → no map; implementer tasks take `Reuse:`, `Delete:`, `Placement:` from scout briefing where it names them. After scout, before decision record; `dl-architect` in map mode (`prompts.md`), or orchestrator itself from scout briefing for a single unit (using MCP architecture-analysis tools if any, as `dl-architect` does); scoped to the change's surroundings, never the whole project. Map: **Fit** (module or layer owning feature's data, with evidence); **Reuse** (existing symbols to extend or call); **Delete** (code feature makes obsolete or a refactor merges away); **Prep refactor** (structural changes making feature smaller or removing a concept, each justified by this feature: generality only when second consumer exists or contract requires it); **Paths** (bolt-on vs refactor-then-feature: net code and test lines, concepts added and removed, files and contracts touched); **Risks** (thin test coverage of area to refactor → characterization tests first). Reuse, Delete, Placement go into implementer tasks (`tiered-fanout` §4); reviewers check diff against map (§3).
- **Path choice.** Prep refactor inside feature's own files, changing no contract, path no larger than bolt-on → orchestrator decides, records it. Refactor reaching other modules, changing a public, wire or persisted contract, or making total change larger → design proposal to user (below); conservative option: bolt-on with map's Reuse and Delete.
- **Refactor unit.** Chosen prep refactor = own unit, run first, in simplify mode; acceptance = map's size and removed concepts. Once it passes review: its own full gate (red → fix round, §2 steps 4–8, gate again), then commit. Feature units branch from that commit; it is their review `<base>`, so their diff and blast radius exclude refactor; landed refactor code = existing code for their reviewers.
- **Size.** Record repo's test pathspec (e.g. `tests/ '**/*_test.rs'`) and each unit's budget: expected net code and test lines, `net-negative` in simplify mode. Measured after `add -N` (§2 steps 2 and 6): `git -C <worktree> diff --numstat <base>`, summed code vs tests by pathspec. Over budget → implementer asks (ask rule), never automatic failure; orchestrator raises budget with reason, or narrows work.
- **Simplify mode**: requests to simplify, reduce or clean up, and every refactor unit. Contract: behaviour unchanged, net code lines down. Existing tests decide correctness; new tests only as characterization tests for uncovered code being changed. Reviewer lenses: Intent, Correctness (behaviour preserved), Simplicity, Duplication. Finding whose fix adds code (characterization tests aside) → out of scope unless it fixes a regression the unit caused. Acceptance: numstat shows net code reduction.
- Units in parallel → one worktree per unit (§6).
- Decide whether implementers can build and run tests in this environment; say so in every task (`tiered-fanout` §4 template). Can → they run targeted tests only, reviewers write probes (§3). Cannot → orchestrator proves each regression test fails (§2 step 6). Nobody runs full test suite before §7 step 1, except refactor unit's own gate (above).
- **Entry from triage.** Approved batch from `triage-findings`: each group in batch (rows sharing owning file or root cause) → one unit, kept whole; sweep group → one sweep unit. Table's difficulty hints → `tiered-fanout` as tier hints.
- **Entry from optimize.** Accepted `optimize` change = one unit, already implemented and gated in its perf worktree. Start at §2 step 3 on `git -C <worktree> diff main`, plan of `optimize` §0 as contract document; run steps 3–8 until verdict meets bar; then full gate once in perf worktree (§7 step 1; fallout → fix round, then full gate again). Orchestrator commits fixes on perf branch, reports every fix touching measured path. §5 integration and rest of §7 do not apply: out-of-scope findings → backlog; `optimize` does measurement, record, merge. At round cap: no takeover round; stop, hand back to `optimize`, which rejects the change. No architecture map, no design rethink (§2): reviewer's `DESIGN: rethink` evidence goes into hand-back, as candidate for a later `optimize` step.

### Loop size

Change size sets which steps apply. Round check, review, final full gate never skipped at any size; in doubt take larger column.

|Step|Trivial|Single unit|Multi-unit|
|---|---|---|---|
|What it is|no behaviour change: doc or comment wording, a rename, in one or two files|one file-disjoint unit|several units, in parallel|
|Decision record (§0)|request is the record|written and committed when spec left anything open|written and committed|
|Scout (§0)|no|when code map unknown|when code map unknown|
|Architecture map (§0)|no|only on a redesign signal (§0); orchestrator may write it|only on a redesign signal (§0), by architect agent|
|Refactor unit (§0)|no|when chosen; own full gate before feature|when chosen; own full gate before feature units|
|Worktree (§6)|no, current checkout|no, current checkout|one per unit|
|Implementer (§2 step 1)|one, usually Light|one, or several file-disjoint items through `tiered-fanout`|one or more per unit|
|Round check (§2 steps 2 and 6)|yes|yes|yes, per unit|
|Full gate with full test suite (§7 step 1)|once, after review passed|once, after review passed|once, on integrated result after every unit passed review|
|Reviewers (§3)|one|one; two split by lens when §3 calls for it|per unit; two split by lens when §3 calls for it|
|Live smoke (§7 step 2)|no|when observable behaviour changed|yes|
|Minor sweep (§7 step 3)|no|only with input|only with input|
|Final report (§7 step 4)|three lines: what changed, gate result, last verdict line|full|full|

### Design proposals to the user

Path choice (above) and design rethink (§2) ask user the same way. Use ask tool to show user the proposal (current vs proposed design, findings it covers, size table, contracts touched) and get approval; preselect conservative option. Before asking, dispatch every other unit's current round; this unit waits. No answer, cancelled, or no ask tool → conservative option; final report records user did not decide. Approved → proposal becomes unit's decision record. Rejected → recorded with user's reason like a rejected finding (§1 convergence rule: reviewers never re-raise it); proposal → backlog (§4).

## 1. Stop condition (state it, quote it)

Default bar: **loop until no critical, major or minor finding remains.** Nits optional (apply cheap ones). User names different bar (e.g. only blocker/major) → use theirs. Restate active bar in first message to each implementer and reviewer; **quote last verdict line in every status report**. Never end a turn on a menu ("shall I fix these or open a PR?") while stop condition unmet: keep looping; ask only about things outside the instruction (push, merge) and design proposals (§0).

### Severity scale (put it in every reviewer prompt)

|Severity|Meaning|
|---|---|
|critical / blocker|wrong behaviour, data loss, security hole, broken build/gate, violated MUST rule|
|major|requirement unmet; regression; observable behaviour with no test; a stale *contract* (docs, schema, migration header, another unit's spec); a reimplemented primitive; logic duplicated so the copies must change together; an upward or cyclic dependency; hot-path cost the rules forbid; code the contract did not need (layer, option, wrapper or abstraction with one caller; parallel path beside code the change should have modified; guard for a state callers or types rule out; compat shim for an internal caller)|
|minor|stale comment/doc wording, near-duplicate test setup, dead code left behind, small simplification, code in the wrong module with no dependency broken|
|nit|taste; optional|

Reviewers strict but evidence-based: critical/major only for real correctness, regression, data-loss, security or rule violations, and design defects the scale names; each with `file:line`, evidence, concrete fix. Design findings ranked by what next change will cost, never by taste. Findings the code does not support are not findings.

### Convergence rule for later rounds

"Block on every minor" does not converge if every fix round spawns new comment drift. From round 2 on, finding is critical/major/minor **only if** it is (a) regression the unit's own changes caused (including a fix breaking an earlier accepted fix), (b) requirement clause still unmet, or (c) defect on a line the unit added or changed, or in its blast radius (§3). Anything else: `pre-existing:` → backlog (§4). No new nits from round 2 on. Reviewers MUST NOT re-raise a finding the fixer or orchestrator's triage rejected *with a reason* unless they show why the reason is wrong; MUST NOT reopen a fix an earlier round accepted. Acceptance, rejection or backlog entry covers the code path it was made for; same weakness on a path the unit adds = new finding.

## 2. The per-round protocol

1. **Implement.** Dispatch units through `tiered-fanout`: one implementer per unit, spawned as its tier's agent (`tiered-fanout` §2 and §4), briefed with new-work template of `tiered-fanout` §4 (`Spec:` = unit's decision-record ids; `Size:` = unit's budget; `Reuse:`, `Delete:`, `Placement:` from architecture map or scout briefing, §0) plus active bar. Implementers ask orchestrator when unsure or blocked; send struggle handoff when work is beyond them; answer or re-assign one step up per `tiered-fanout` §5.
2. **Orchestrator round check + spot-read.** Run round check: format, lint, build, no test suite (yourself or via `dl-runner`, reading its raw output); read diff and targeted tests implementer reports it ran. Red → apply a fix the tool prints, as top of this skill allows; else send exact failure back to implementer. Never review red code. Then run `git -C <worktree> add -N .` (intent-to-add, stages no content) so files implementer created appear in `git diff`; then measure size (§0) against unit's budget.
3. **Review.** Fresh `dl-reviewer` agent(s) scoped to diff and its blast radius (§3). Required output:
   - findings with severity, `file:line`, evidence, fix; for a probe-proven finding, probe's path and run command;
   - `## Out of scope` section;
   - `## Not checked` section: assigned lenses or areas not covered and why; each suspicion neither reading nor probe settled, with command that proves it and platform it needs; each untracked file the diff does not show;
   - `## Could be deleted` section: added lines no severity covers (comments restating code, redundant locals, verbose constructs with a shorter equivalent); never blocks;
   - line `DESIGN: keep` or `DESIGN: rethink — <evidence>` (Design rethink, below);
   - line `TIER: keep` or `TIER: up — <reason>` for next fix round (§3);
   - last line `VERDICT: PASS` (nothing at or above bar) or `VERDICT: FIX`.
4. **Triage every finding yourself.** First settle `## Not checked`, on every review, PASS included: run each command it names (yourself or via `dl-runner`; targeted commands, never full suite), failure = finding; send uncovered lens or area back to a reviewer; `git add -N` an untracked file belonging to the unit and have it reviewed, drop one that does not. Leave `dl-probe` file of each finding triaged as fix in place for its fixer; delete probe of a finding you reject or accept as is, and any probe no finding points to. Item closes only by a run or a trace that proves it: "probably", "inferred", "fails closed" close nothing. What cannot be run here (another OS) or stays unverified → final report as residual risk (§7 step 4), with platform and what would prove it. Then per finding: fix | reject with reason | spec wrong → write decision and amend | accept as is. Prefer a fix that changes or deletes code over one that adds; minor whose fix adds more code than the risk it removes (extra logging, validation at an internal boundary) → accept as is, with reason. Each `## Could be deleted` item: fix item or reject with reason. You make the design call; do not hand fixer an open question. Reviewer-prescribed fix = proposal: before binding it, check what it changes beyond the finding (other run modes, platforms, shared pools and limits).
5. **Fix.** Dispatch every finding triaged as fix to fixer subagents through `tiered-fanout`, in one batch, even a one-line or doc-only fix; orchestrator edits in this step only in cases listed at top of this skill.
   - Each finding with its binding decision = work item, tiered by difficulty (`tiered-fanout` §2).
   - Who gets it (live implementer session or fresh fixer, at which tier, including after reviewer's `TIER: up`): reuse rule of `tiered-fanout` §4 and escalation ladder of `tiered-fanout` §2.
   - Fixers edit working tree, never commit. Fix changing behaviour adds a regression test failing before the fix, proven by temporarily swapping in the plausible bug, seeing it fail, reverting (by fixer, or by orchestrator in step 6 where fixers cannot run tests). Fix changing no behaviour (deletion, inlining, simplification, wording) adds none: existing tests decide.
   - Probe-proven finding goes to its fixer with probe's path and run command: fixer reproduces with it, fixes, carries case into regression test, deletes probe (Probe lifecycle, top of this skill); probe is in fixer's files.
   - Fixers run targeted tests only (table at top of this skill), never full suite.
   - Struggling fixer sends struggle handoff (`tiered-fanout` §5).
   - Fanout reports per item (`tiered-fanout` §8); its round check and fallout (`tiered-fanout` §7) = steps 6–8 here; step 4 here supplies its decided inputs (`tiered-fanout` §1).
6. **Orchestrator round check + read the fix** before re-review. Where fixers could not run tests, run each break they reported: apply it, run named test, see it fail, revert; test still passing → back as finding. `dl-probe` file of a fixed finding still present → back to its fixer. Then run `git -C <worktree> add -N .` again so files the fix created appear in diff; measure size again (§0).
7. **Re-review.** Same reviewer session (or fresh one for independent eyes on later rounds): verify each prior finding resolved (by fresh probe where possible) **and** re-read whole current diff for anything the fix introduced; each fix reviewed as new code, reviewer-prescribed fixes included. Re-review prompt carries fixers' `## Design friction` notes. Harness cannot message reviewer → spawn fresh one with round-1 prompt, its previous report, and re-review block.
8. Repeat 4–7 until verdict meets bar and last review's `## Not checked` settled (step 4); failed check reopens loop.

**Cosmetic tail.** From round 2 on, when at most two items remain open and each is a comment, a doc line changing no stated fact, a format fix, or a no-behaviour change compiler or lint verifies (narrower visibility, unused import removed, large variant boxed): orchestrator fixes them inline and confirms with round check instead of another review round. Record they were not re-reviewed. Round-1 findings, more than two items, or anything touching behaviour → step 5.

**Round cap.** Three automatic fix rounds per unit; escalation inside them per `tiered-fanout` §2. **Cap wins over ladder**: item started at Light can reach cap at Standard without ever running on Deep. Still failing → last review carries `DESIGN: rethink` → design rethink first (below); otherwise, or no restructure approved → stop, summarise remaining findings, make a **takeover round**: orchestrator takes unit over, works without subagents (read review, verify each finding, fix in working tree, run targeted tests and round check, as a fixer would), then runs review again: its own fixes regress too. Unit's commit stays the one §5 describes, made once loop passes. Finding it also cannot resolve, or one needing operator decision → user, with remaining findings; loop stops there.

**Design rethink.** One trigger: reviewer's `DESIGN: rethink — <evidence>` line, raised only when findings make a redesign most probably necessary or clearly recommended (design-evidence rule of `dl-reviewer`; with an architecture map, cites the map section the evidence contradicts). Round cap, finding count, and fixers' `## Design friction` notes trigger nothing: re-review prompt carries friction notes, reviewer judges them. Not in optimize entry (§0). On trigger: spawn `dl-architect` in rethink mode (`prompts.md`) with unit's diff, the DESIGN line, open and accepted findings, map if any; it reads only code those touch. Proposal reaches user only when it resolves at least two open findings or one recurring finding, **and** leaves less code or fewer concepts (types, layers, flags, modules); otherwise → final report, Needs your attention, and loop goes on. Passing proposal → user (§0 Design proposals); conservative option: minimal fixes (at round cap: takeover round), proposal to backlog.
- Approved: before dispatch, snapshot unit: commit only the unit's files, no `dl-probe` file (`git -C <worktree> add -- <unit's files>`, commit `wip: pre-restructure`); record sha and numstat; revert = `git -C <worktree> reset --hard <sha>`. Unit's commit (§5) squashes the snapshot. Restructure = new work, Deep (`tiered-fanout` §2; pure deletions inside it Light); round-1 rules, round cap reset once. Touches a parallel unit's files → re-partition (§5) or restructure after integration.
- Acceptance = proposal's stated net code and test lines and removed concepts, measured by numstat against unit's diff from before restructure; Intent lens checks removed concepts gone. Result larger than stated → report actual numbers to user, ask: continue or revert to minimal-fix path.
- At most one rethink per unit.

## 3. Reviewer setup

- Spawn `dl-reviewer` agent (`develop-loop:dl-reviewer` in Claude Code; model routing per harness in `tiered-fanout` §4). It carries read-only and probe rules, evidence rule, review lenses, ask rule, output format (findings, `## Out of scope`, `## Not checked`, `TIER:`, `VERDICT:`). Without plugin agents: paste its body at top of reviewer prompt; set reviewer's model and effort from agent table in `tiered-fanout` §4. Read-only except probes: no edits to tracked files, no commits, never full test suite, project's tests or gate (orchestrator owns gate); runs only its own probes.
- **Probes.** Where agents can build and run tests here (§0), give reviewer a `Probes:` command running one of its own probe files (through build wrapper of §6 when units run in parallel). Checks parsing input differently from the code they guard, hangs, escapes: show only when something runs. Probe proving a finding stays in worktree for fixer; finding points to it (Probe lifecycle, top of this skill). Reviewer deletes only probes that proved nothing.
- **Scope to diff and its blast radius**, diff stated as command: `git -C <worktree> diff <base>` (working tree vs unit's base, so uncommitted changes included; new files show because of `add -N` in §2 steps 2 and 6). Findings on lines diff adds, changes or removes, and in its blast radius (callers, callees, consumers of what changed code produces, entry points and run modes reaching it, old code it newly exposes to untrusted input) where the change causes, exposes or relies on the defect; such finding cites both lines; fix outside unit's files follows ownership rule of `tiered-fanout` §5. Reviewer also reads beyond diff for existing implementations and placement.
- Give a `Check especially:` list of risks this unit can break: worst-legal-input bounds, shutdown/lifecycle, error shapes, authz, caching, test determinism, etc. A floor, never the scope. Unit on a trust boundary: add `Threat model:` line (who is untrusted, what they control: files, paths, input, timing); word risks as attacks ("what does the host do with a file the contained code controls?"), not functions ("can the hook write there?").
- Run **two reviewers split by lens** on units changing behaviour or mixing kinds of work (implementation vs tests, or code vs docs/CSS); Trivial change (§0) always takes one. Each prompt names its lenses from `dl-reviewer` list. (A single reviewer who already saw the code missed a test-coverage major a second one caught.)
- Tests judged by: *name the concrete pre-fix or plausible-bug behaviour that makes it fail; flag any test that would pass with a buggy implementation.*
- Quote contract documents reviewer must check against (decision record, README, mockup), name repo rules file, say which other units' areas to ignore.
- Architecture map exists → quote it; Intent and Placement lenses check diff against it: Reuse symbol bypassed or duplicated, Delete item left, code outside Placement = finding. Simplify mode (§0) → name its lenses.
- **Reviewer model.** Always `dl-reviewer`'s model (agent table in `tiered-fanout` §4), whatever tier wrote the code. Reviewers not tiered, never escalate.
- Reviewers ask orchestrator when contract or scope unclear instead of assuming; answer also goes into re-review prompt.
- **Reviewers upgrade the fixer's tier.** Reviewer writes `TIER: up — <reason>` or `TIER: keep` on line before final `VERDICT:` line; signals in `dl-reviewer` agent; orchestrator's handling = `tiered-fanout` §2 trigger 3.

## 4. Backlog for everything out of scope

Findings outside diff and its blast radius (§3) never block, never fixed in this loop. They go to `backlog.md` at root of main checkout (never inside a unit's worktree, which is removed at end), **excluded from git** via `.git/info/exclude`, not `.gitignore` (so exclusion itself not committed). Each entry: where, what, which round found it. Backlog belongs to `triage-findings`, which selects next batch from it after the loop; post-loop **minor sweep** (§7) covers only units' own leftovers, never backlog entries.

## 5. Parallel units: ownership and integration

- Parallel units: disjoint file sets; shared contract (signatures, schemas, decision ids) written before dispatch. Slice that must touch another's file says so in its report.
- Subagents stay within their absolute-path worktree (relative paths landed first edits in main checkout twice). After each wave, `git status` in main checkout MUST be clean.
- Integrate by rebasing each unit's single commit onto feature branch and `merge --ff-only`; conflicts are orchestrator's, not findings.
- Commit progressively: one focused commit per unit, made by orchestrator (subagents never commit) once unit's loop passes and its worktree holds no `dl-probe` file; a `wip: pre-restructure` snapshot (§2 Design rethink) is squashed into it.

## 6. Worktrees and build cache

- One worktree per unit, created by tiny script (`git worktree add ../<repo>-wt/<unit> -b fix/<unit>`).
- Share compile/dependency cache so units do not each rebuild from scratch. Rust example: seed each worktree's `target/` as copy-on-write reflink of main one (`cp --reflink=auto -r`), or point all at one `CARGO_TARGET_DIR` or sccache; other stacks: shared package/build cache directory. Cap concurrent builds (lock-slot wrapper, e.g. 2 at once) so parallel units do not thrash the machine; unset env vars the test suite is sensitive to inside the wrapper.
- Remove worktrees and merged branches at end; this step gets forgotten.

## 7. Finish

1. **Full gate, the last full test-suite run** (only earlier one: refactor unit's own, §0). Once every unit passed all its review rounds, run repo's full gate once on integrated result (format, lint, build, full test suite, other checks; yourself or via `dl-runner`), then repo's duplicate/clone detector (finds near-copies parallel agents wrote independently). Failures and clone fixes (extract one helper per pair, never weaken assertions) run as fix round: §2 steps 4–8, fixers again on targeted tests only. Any edit after full gate (that fix round, a smoke finding, minor sweep) re-runs full gate before final report.
2. **Live smoke**: run real system on throwaway instance; exercise changed paths in browser/CLI, through every entry point and run mode reaching them. Code-reading reviews miss rendering and integration bugs; smoke tests caught defects after several clean review rounds.
3. **Minor sweep** for each unit's own leftovers. Run only with input: minors from units' last PASS reviews left open because bar excluded them, or nits you decided to apply (backlog entries go to `triage-findings`, never here). Under default bar a PASS leaves no minors; no nits worth applying → skip sweep, say so in final report. Scope it (inefficiency, stale docs, design-doc divergence, duplication); skip test-style nits and anything needing operator decision; decide every item yourself before dispatch (§2 step 4). Run as one more round: dispatch through `tiered-fanout` with sweep prompt, round check, review sweep diff, fix per §2 steps 4–8, one commit. Sweep never lands unreviewed.
4. Final report: headline (what landed, commit range, size per unit as code and test `+A −R`, gate result, smoke result) → how it ran (rounds per unit, tiers used, escalations, design rethinks and user answers) → one bullet per user-visible behaviour with decision ids → **Needs your attention** (rejected items, divergences, design proposals below bar or not decided by user, backlog summary, residual risk: unverified `## Not checked` items and platforms not run, anything not exercised).

## Failure modes seen

- Orchestrator applies review findings itself because they look small or a spawn seems slower → violates §2 step 5; dispatch fixers. Inline edits limited to cases listed at top of this skill.
- Agent stops after clean-looking round to ask permission → violates loop; keep going.
- Doc claims drift from code between rounds (doc says "returns 404 on a missing item" after code started returning 410; documented limit differs from constant) → reviewers MUST check each doc statement the diff touches against code.
- Prompt-quoted constants/examples propagate wrongly into every slice → verify wire facts with a scout before writing contract.
- Reviewer cannot prove formatting/line-length by reading → let formatter decide.
- Reviewers re-raising rejected findings burn rounds → require rejection reason in fix summary (`## Finding map`: finding → `file:line`/test, or `rejected: reason`).
- A check parsed a path list one way and the tool it guarded another (quoted part, malformed selector); reading both passed it, first throwaway probe broke it → reviewers probe (§3) and compare every check with its use.
- Reviewer-prescribed fix, applied as written, caused next bug (work moved onto capped thread pool; error path hanging one run mode) → fix reviewed as new code (§2 steps 4 and 7).
- `## Not checked` item closed as "probably fails closed" left feature dead on a platform nobody ran → only a run or proving trace closes it (§2 step 4).
- "Is the directory writable for the hook?" got a functional answer; bug was what host did with a file the hook controlled → give a `Threat model:` (§3).
- Unchanged line became exploitable through new code, and a fix closed one comparison of a class but not its siblings → review blast radius (§3); finding lists every instance (`dl-reviewer`).
- Agents asked to simplify added code: parallel path beside the old one, guards for impossible states, tests of wiring for fixes changing no behaviour; each fix round grew unit → size measured every round against a budget (§0), no regression test for no-behaviour fixes (§2 step 5), smallest-change rules in implementer agents, deletions on Light tier (`tiered-fanout` §2).
- Fixes piled special cases onto a structure that did not fit the feature → architecture map before code (§0), design rethink (§2).

See `prompts.md` for copy-ready reviewer, re-review, minor-sweep and architect (map, rethink) prompts; implementer, fix and runner prompts live in `tiered-fanout` §4.
