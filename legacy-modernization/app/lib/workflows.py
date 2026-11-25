"""Named workflow registry + prompt/event builders — pure.

A workflow is a named, ordered step pipeline the user launches from the
composer with a leading ``/workflow-*`` (or ``/extract-*``) token. The
WebSocket chat handler recognizes the token, substitutes the built step
prompt for the agent (the transcript keeps the typed command via ``display``),
and seeds the canvas's Workflow tab. The agent reports step transitions by
calling the ``mcp__workflow__update_workflow`` tool, which ``process_message``
intercepts and re-emits as an ``update_workflow`` WebSocket event built here.

AUTHORING A NEW WORKFLOW is declarative — one ``_workflow(...)`` entry in
``WORKFLOWS``. Each workflow carries its own graph:

- ``nodes``: ordered steps, each ``_node(id, title, description,
  instructions)``. ``description`` renders on the canvas card; ``instructions``
  becomes that step's section of the injected prompt. Adding a step (e.g. a
  future ``extractor`` in front of the agent) is inserting one ``_node``.
- ``gates``: zero or more ``_gate(after_node_id, label, ...)`` decision
  diamonds, each anchored after a node, with an optional re-run loop target
  and its own prompt instructions. Multiple gates / multiple outputs are just
  more entries — the canvas renders every gate after its anchor node.
- ``preamble``: the workflow's input contract, injected verbatim.

Scope: the extractor step from the design is NOT
part of the shipped migration pipeline — it starts at the Agent step and
assumes the extraction output (analysis docs, specs, or legacy source) is
already available in the conversation. This module is intentionally
side-effect-free so it can be unit-tested in isolation.
"""

from __future__ import annotations

# Leading tokens with any of these prefixes are treated as workflow commands:
# the launchable migration pipeline lives under /workflow-*, and the extraction
# pipeline under /extract-*.
WORKFLOW_COMMAND_PREFIXES = ("/workflow-", "/extract-")

# Node statuses the agent may report. Anything else is coerced to "pending" so
# a malformed tool call still produces a renderable graph.
WORKFLOW_NODE_STATUSES = frozenset({"pending", "running", "done", "failed"})

# Gate fields that exist only to compose the agent-facing prompt / refusal —
# never sent to the frontend (see _public_gates).
_GATE_PROMPT_FIELDS = ("instructions", "loopPrep", "requirementsFromReport")

# The validator step writes an INTERMEDIATE Implementation Report: the same
# document the report step finishes, same skeleton, ids and KPI cards, named
# `<AppName>-r<revision>` + this suffix. The validator gate reads its
# "REQs implemented" figure (the spec ids whose appendix-Z row answers Implemented
# Yes, over every spec id; IN-nn/CAP-nn rows don't count; the number the page-1
# card shows) instead of trusting a pass rate the run reports about
# itself, so a report reading 5% can't follow a passed gate.
INTERMEDIATE_REPORT_SUFFIX = "-intermediate-report.md"

# Gate policy defaults: the validator scores the generated app against the
# extraction input's business requirements, business rules AND user journeys;
# the run passes
# the gate at >= PASS_THRESHOLD_PCT and may loop back to the agent step at
# most MAX_RERUNS times before proceeding with the gaps recorded in the report.
MAX_RERUNS = 5
PASS_THRESHOLD_PCT = 95

# The design-fidelity gate is separate from the functional validator gate and
# scores a different thing: how faithfully each built screen matches its Figma
# frame (visual + structural + component detail), NOT whether features work.
# A functionally-complete app that looks nothing like the design must NOT ship,
# so the bar mirrors the functional gate: >= this % of screens PASS fidelity
# (for a typical 8-12 screen app that still effectively means every screen).
# It shares the MAX_RERUNS budget shape with its own counter.
DESIGN_PASS_THRESHOLD_PCT = 95


def _node(
    node_id: str,
    title: str,
    description: str,
    instructions: str = "",
    info: list[str] | None = None,
) -> dict:
    # `instructions` feed the composed step prompt (agent-facing prose);
    # `info` is the curated bullet list behind the node card's info icon
    # (user-facing). Nodes without `info` fall back to their instructions.
    return {
        "id": node_id,
        "title": title,
        "description": description,
        "instructions": instructions,
        "info": list(info or []),
    }


def _gate(
    after_node_id: str,
    label: str,
    *,
    re_run_target_id: str | None = None,
    yes_label: str = "YES",
    no_label: str = "NO · RE-RUN",
    instructions: str = "",
    threshold_pct: int | None = None,
    max_reruns: int | None = None,
    loop_prep: str | None = None,
    requirements_from_report: bool = False,
) -> dict:
    gate = {
        "afterNodeId": after_node_id,
        "label": label,
        "yesLabel": yes_label,
        "noLabel": no_label,
        "instructions": instructions,
    }
    # What the run must produce BEFORE looping back, quoted verbatim in the
    # refusal (see gate_accounting_violation). Defaults to the migration
    # pipeline's intermediate progress report; a gate scoring something else
    # overrides it so the refusal never asks for an artifact that makes no sense
    # in that run.
    if loop_prep:
        gate["loopPrep"] = loop_prep
    # The gate's pass rate is capped by the intermediate Implementation Report's
    # requirements figure (see gate_accounting_violation).
    if requirements_from_report:
        gate["requirementsFromReport"] = True
    if re_run_target_id:
        gate["reRunTargetId"] = re_run_target_id
    # A thresholded gate carries machine-checkable pass criteria: the agent
    # must report pass_rate_pct + reruns_used when crossing it, and the
    # update_workflow tool REFUSES a crossing that violates the loop budget
    # (see gate_accounting_violation). Gates without a threshold are prose-only.
    if threshold_pct is not None:
        gate["thresholdPct"] = threshold_pct
        gate["maxReruns"] = max_reruns if max_reruns is not None else MAX_RERUNS
    return gate


def _migration_nodes(source: str) -> list[dict]:
    """The shared migrate-a-legacy-app pipeline: agent → validator → report."""
    return [
        _node(
            "agent",
            "Agent",
            f"Generate the OutSystems app (OML) from the {source} extraction input",
            "Generate the OutSystems app from the extraction input. Locate and "
            "read the extraction input first — including the BUSINESS-RULES "
            "and USER-STORIES SOURCES named in the preamble: implement EVERY "
            "individually-identified rule and story, and keep a per-item trace "
            "in your workspace notes (rule/story id → the entity/action/screen "
            "that implements it) so the "
            "validator and the report can verify each one. WHEN SUBAGENTS ARE AVAILABLE, run "
            "the full team choreography and do NOT jump straight to building or "
            "planning: designer (emit/patch the design options) → design-selection "
            "pause (show the options and let the user pick straight away; no QA "
            "runs before the pick, so the choice is fast) → pre-build DESIGN GATE "
            "on the PICKED option only (the reviewer scores spec + screen-coverage + UX principles, "
            "then the tester runs visual QA, looping fixes back to the designer "
            "until both pass) → planner (macro plan + modernized spec) → developer "
            "builds the app, looping reviewer(app) then tester(app). The pre-build "
            "design gate (reviewer + tester over the picked design) is MANDATORY "
            "before any DESIGN-DEPENDENT planning or building — skipping it, or "
            "planning screens against a picked design that is not yet gated, is a "
            "workflow violation. It does NOT gate the design-independent slice "
            "described next. See "
            "the orchestrator team guide for each role's contract. "
            "THAT ORDER GATES THE DESIGN-DEPENDENT WORK, NOT THE WHOLE BUILD — "
            "read it as a dependency chain, not as a queue in which only one role "
            "may be working. Two overlaps are not only allowed but expected, "
            "because the wall-clock before the user can open a running screen is "
            "itself a deliverable. (a) THE DESIGN-INDEPENDENT SLICE RUNS "
            "ALONGSIDE THE DESIGN LOOP: creating the app, the entities the "
            "data-model slice defines and their per-entity seed rows is grounded "
            "in the SPEC, not in the palette, so dispatch it to the developer "
            "while the designer, the gate and the selection pause are still in "
            "flight. What stays behind the pick is everything design-bearing — "
            "the Theme, the shared chrome, and any screen carrying design claims. "
            "(b) THE DESIGNER KEEPS DESIGNING AFTER THE PICK: options cover a "
            "REPRESENTATIVE SET of screens (the screen the build publishes first, "
            "one screen exercising a different pattern, the dashboard when there "
            "is one — see the designer guide), the user picks from that set, the "
            "gate runs on the picked option's screens, and the remaining screens are designed for the CHOSEN option "
            "only, while the developer builds the earlier ones. The coverage law "
            "is unchanged and is enforced per screen: every navigation target and "
            "CRUD screen still gets its own design, and NO screen is built before "
            "its own design exists. The GATE is per screen too — each design that "
            "lands after the pick goes through the same reviewer (spec/coverage) "
            "and tester (visual QA) pass as the picked option's first screens did, before the "
            "developer builds that screen. A design drawn mid-build that nobody "
            "reviewed is the hole this overlap would otherwise open. WITHOUT "
            "subagents, do it yourself end-to-end — but the pre-build design "
            "review + visual-QA gate is STILL mandatory: once the user picks, apply "
            "the reviewer + tester playbooks inline to the PICKED design "
            "(spec/coverage compliance, UX principles + visual QA) and fix it BEFORE you build, "
            "then build via the OutSystems Mentor flow following the "
            "outsystems-app-build skill — FIRST SCREEN FIRST (that skill's rule "
            "6): order the work so the first publish is already a screen the user "
            "can open and navigate (the app, the one entity it reads, its seed "
            "rows, that screen), then extend, ONE CHUNK → ONE PUBLISH → ONE "
            "DRIVE-TEST, instead of building every entity and every screen and "
            "publishing once at the end. Report the published URL as soon as that "
            "first screen is live, and again on every later publish — the user "
            "should be able to open the app while the run is still going. WHEN FIGMA "
            "IS IN SCOPE, also invoke Skill `ui-exactness` before any Mentor "
            "UI / Theme turn: literal hex/px CLAIMS, design-pack or DesignBrief "
            "claim tables (same shape as "
            "`skills/ui-exactness/design-pack-templates.md`), "
            "DOM-before-CSS on OSUI chrome, one publish then claim verify — "
            "no soft 'closer to Figma' remold loops. This step owns ALL the work: do your "
            "own smoke checks and fix everything you find BEFORE marking the "
            "step done — the Validator that follows only scores, it never "
            "fixes; anything you leave broken becomes a FAIL at the gate and "
            "loops the whole step back to you. Keep the north-star (macro) plan "
            "LIVE from the very start: your FIRST action — before any discovery, "
            "design, or delegation — is to declare the macro plan "
            "(mcp__plan__update_plan, level macro, coarse phases as steps, "
            "current_step 1) so the Plan canvas is never stuck on 'No plan yet' "
            "while you work; then re-call it on the SAME macro plan_id to advance "
            "current_step as each phase completes — never leave it parked on "
            "step 1, and keep the active macro step matching the sub-plan "
            "currently in flight. GRANULARITY: every plan you or a subagent "
            "emits carries ONE ITEM PER INDIVIDUALLY-IDENTIFIED THING — one per "
            "requirement, business rule, user story, screen, entity, "
            "relationship, seeded entity, action, error path and test — each "
            "titled with its source id where the specs number them. The canvas "
            "is the run's working memory, so a bucket item that stands for many "
            "('Implement the business rules', 'Build the screens', 'Test the "
            "app') is work that gets forgotten and scope the user cannot see; "
            "a 60-item plan is the correct plan.",
            info=[
                f"Reads the {source} extraction input (analysis, specs, source, or Figma design)",
                "Implements every business rule and user story from their spec sources (04-business-rules.md, 06-user-stories.md, requirements.json) with a per-item trace",
                "With a team: designer → you pick → design gate (reviewer + tester review the picked design) → planner → developer",
                "The pre-build design gate is mandatory — the picked design is spec-checked and visually QA'd before the screen it describes is built",
                "You pick from a representative set of screens, not a full set — the rest of the chosen design is drawn while the build is already running",
                "Creates the app, the data model and the seed data straight away, in parallel with the design — none of it depends on the look",
                "First screen first: the first publish is a screen you can open and navigate, not an empty data model",
                "Builds the remaining screens and logic via the OutSystems Mentor flow, one chunk → one publish → one drive-test",
                "When Figma is in scope: Skill ui-exactness (CLAIMS + claim tables) before Mentor UI/Theme",
                "Publishes on the tenant continuously and posts the URL, so you can open the app while the run is still going",
            ],
        ),
        _node(
            "validator",
            "Validator",
            "Score the app against the extraction input's business requirements, "
            f"business rules and user journeys — gate passes at ≥{PASS_THRESHOLD_PCT}%",
            "Validator: independently score the generated app against the "
            "extraction input. This step is READ-ONLY — it NEVER fixes, "
            "edits, publishes, or starts a mentor run; a defect found here "
            "is recorded as FAIL and the gate decides what happens (fixes "
            "belong to the agent step, via the gate's re-run loop). Run it "
            "from a CLEAN CONTEXT: the validation is briefed with ONLY (a) "
            "the SPEC FILE PATHS — the extraction-input files from the "
            "launch turn (analysis docs, modernized spec, uploaded source, "
            "or the design handoff) — and (b) the running app's URL. No "
            "build history, no assumptions carried over from the build; "
            "score with FRESH evidence gathered by navigating the app now — "
            "never reuse the build step's observations as PASS evidence. "
            "The validation READS THE SPEC FILES ITSELF — ALL of them, every "
            "slice of an extractor collection (00-overview.md … "
            "12-unknowns.md), never a sample — and enumerates an "
            "explicit checklist of the BUSINESS REQUIREMENTS and USER "
            "JOURNEYS they define — never score against a checklist "
            "pre-digested by the build step (the builder summarizing its own "
            "work re-introduces the bias this step exists to remove). Then "
            "verify each item against the running app (drive it, don't assume) "
            "and mark it PASS or FAIL. At minimum, the checklist covers: "
            "screen navigation (every screen opens, menu routes correctly), "
            "search / filters / dropdown filters, table pagination, table "
            "sorting, and CRUD round-trips (created/edited/deleted records "
            "persist). When the specs carry a BUSINESS-RULES SOURCE — the "
            "extractor's 04-business-rules.md slice, any other file holding "
            "the rules (Glob for it — e.g. business-rules.md, the rules "
            "section of the Business Spec or the modernized spec), or the "
            "rule entries in requirements.json — the checklist ALSO carries "
            "ONE ITEM PER INDIVIDUAL BUSINESS RULE: drive the app into the "
            "rule's trigger condition and assert its expected outcome (the "
            "validation rejects the input, the computed value or status "
            "transition lands, the restriction holds). A rule that cannot "
            "be driven to a verdict is a FAIL with the reason recorded — "
            "never silently dropped from the checklist. Likewise for the "
            "USER-STORIES SOURCE (the extractor's 06-user-stories.md slice, "
            "any user-stories file, or the story entries in "
            "requirements.json): ONE ITEM PER INDIVIDUAL USER STORY — drive "
            "the journey the story describes end-to-end and assert its "
            "acceptance criteria; story items are the user-journeys side of "
            "the combined checklist, keyed by story id, under the same "
            "no-silent-drop rule. Beyond the two per-item sources, sweep the "
            "REMAINING implementable spec files for coverage: every "
            "entity/attribute the data-model slice defines, every screen, "
            "every role/access rule, every workflow/process, every "
            "integration is verified present in the app or recorded as a "
            "FAIL with the gap named. Verify UI-observable items by driving "
            "the app; a data-model item that never surfaces in the UI (an "
            "FK, an audit field, an internal status) is checked via the "
            "same read-only Mentor inspection as the MainFlow check below — "
            "and when it can't be observed either way, record it NOT "
            "OBSERVABLE and exclude it from the pass-rate denominator, "
            "never guess and never blind-FAIL it. CATEGORY WINS OVER FILE: an "
            "item is scored by WHAT IT IS, not the file it sits in. A "
            "requirement, rule, user story, entity/attribute, screen, "
            "role/access rule, workflow/process or integration is a checklist "
            "item even when it's written inside a meta slice — e.g. an "
            "access-control or roles requirement that happens to live in "
            "09-non-functional.md is STILL scored (it's a role/access rule), "
            "and a mandatory-FK note there is a data-model item. Only genuinely "
            "meta content adds NO checklist item: narrative overview, migration "
            "disposition, agentic suggestions, unknowns, and non-functional "
            "ASPIRATIONS with no observable behaviour. So 'meta slices add no "
            "items' means by CATEGORY, not by filename — never drop a real "
            "role/access/data-model requirement just because it was filed under "
            "a meta slice. PARTIAL and NOT OBSERVABLE are distinct verdicts: a "
            "PARTIAL (some acceptance criteria driven, >=1 not) counts as NOT a "
            "pass in the rate (never round up to PASS); a NOT OBSERVABLE is "
            "excluded from the denominator entirely. "
            "Beyond the drive-test matrix, verify the BUILD "
            "CONVENTIONS: the MainFlow canvas arranges the screens as a "
            "matrix/grid (rows of 3-4, grouped per entity — a read-only "
            "inspection via the Mentor flow, not the running app; one long "
            "line is a FAIL), and the entities (ER) diagram was produced "
            "(entities plus relationships spelled out). Compute the pass "
            "rate over the combined checklist. "
            "PUBLISH THE CHECKLIST TO THE PLAN CANVAS BEFORE SCORING "
            "ANYTHING: as soon as the checklist is derived — and BEFORE the "
            "first mcp__preview__agent_browser call — call "
            "mcp__plan__update_plan with "
            "plan_kind 'detailed' and a `test` section holding ONE ITEM PER "
            "CHECKLIST ENTRY, each titled with its source id (e.g. 'BR-07 — "
            "Overdue loans block new checkouts', 'US-03 — Member reserves a "
            "book'). The user must see every individual requirement, rule and "
            "journey that is going to be tested, by name, before the run "
            "starts — a single bucket item ('Revisit business requirements', "
            "'Revisit user journeys', 'Test the app') is a bug: it hides an "
            "unknown amount of work behind one checkbox and is how checks get "
            "silently dropped. A spec with 30 rules and 12 stories yields at "
            "least 42 items, not two. Then flip each item in_progress when you "
            "start driving it, done ONLY on a PASS, and `failed` when the check "
            "was driven and did NOT pass (reason in its description) — never "
            "`done` (that hides it) and never left on in_progress (that reads "
            "as still-working); the canvas renders failed items in red with a "
            "per-section 'N failed' count. A check you conclude CANNOT be "
            "driven (a race, a rollback needing a half-failed transaction) is "
            "`not_observable` with the reason in its description — a verdict, "
            "not work in flight: it renders grey, counts as settled so the bar "
            "and the ring can complete, and matches the TestReport, which "
            "excludes it from the pass-rate denominator. PARTIAL takes "
            "whichever fits: `failed` if the part you drove broke, "
            "`not_observable` if the rest can't be reached. "
            "The canvas items and the TestReport's flows[] are the same "
            "list, matched by source id. "
            "Delegate to the tester subagent when available — its fresh "
            "context IS the clean-context guarantee; brief it with JUST the "
            "spec file paths and the app URL (it has Read/Glob/Grep to read "
            "the specs and derive the checklist itself), and tell it to "
            "publish that checklist to the Plan canvas one item per check "
            "before it drives. "
            "THEN WRITE THE INTERMEDIATE IMPLEMENTATION REPORT — this is the "
            "validator's report, and the gate reads it: the SAME document the "
            "report step finishes, written the same way (the reporter's "
            "skeleton, its fixed status vocabulary, the spec's ids unchanged, "
            "the page-1 KPI cards including `- **P% REQs implemented** X of N "
            "spec ids`, appendix Z and its `Implemented: X of N. Tested: Y of M.` "
            "totals), from this scoring's TestReport and the BuildReport. Name "
            "it <AppName>-r<revision>-intermediate-report.md for the revision "
            "you scored, title it '<App> — Requirements & Implementation "
            "Report (intermediate, validator loop <reruns_used>)', and open its "
            "lead quote with 'Intermediate report: the validator gate's "
            "scoring of revision <revision>; the final report is this one, "
            "made final.' Delegate it to the reporter subagent in INTERMEDIATE "
            "mode when available (brief: the TestReport, the BuildReport, the "
            "spec file paths), render it with render_pdf (which refuses a "
            "report whose ids or appendix-Z totals don't match the spec) and "
            "surface it via show_file. Write it on every validator pass, "
            "including each re-run loop: the latest one is what the gate "
            "reads.",
            info=[
                "Read-only: never fixes, edits or publishes the app — a defect found here becomes a FAIL for the gate (the step's one write is the intermediate report below)",
                "Runs from a clean context: briefed with only the spec files + the running app's URL",
                "Reads the spec files itself and derives its own checklist — never scores against the builder's summary",
                "Builds an explicit checklist from the specs' business requirements, business rules + user journeys",
                "Publishes that checklist to the Plan canvas BEFORE testing — one item per individual requirement, rule and journey, named with its source id (never a 'Revisit business requirements' bucket)",
                "Flips each item live as it runs: in_progress while driving, done only on a PASS, failed when a check was driven and did not pass, not_observable when it concluded the check cannot be driven at all (reason on both)",
                "Enumerates every individual business rule from the business-rules source (04-business-rules.md, requirements.json, or any rules file in the specs)",
                "Tests each business rule one by one — drives its trigger condition and asserts the expected outcome",
                "Enumerates every individual user story from the user-stories source (06-user-stories.md, requirements.json) and drives each story's journey end-to-end",
                "A rule or story that can't be driven to a verdict is a FAIL with the reason — never silently dropped",
                "Sweeps the remaining implementable spec files — entities, screens, roles, workflows, integrations verified present or recorded as gaps; meta slices inform the report, not the gate",
                "Verifies every item by driving the running app — fresh evidence, never reuses the build step's",
                "Tests screen navigation: every screen opens, menu routes correctly",
                "Tests search, filters and dropdown filters return matching rows",
                "Tests table pagination and sorting",
                "Tests CRUD round-trips: created/edited/deleted records persist",
                "Checks the MainFlow canvas arranges screens as a matrix/grid, not one long line",
                "Checks the entities (ER) diagram was produced",
                f"Marks each item PASS/FAIL and computes the pass rate for the ≥{PASS_THRESHOLD_PCT}% gate",
                "Writes the intermediate Implementation Report (<AppName>-r<rev>-intermediate-report.md): the final report's structure and KPI cards, marked intermediate",
                f"The ≥{PASS_THRESHOLD_PCT}% gate reads that report's 'REQs implemented' figure, so the final report can't show less than the gate passed on",
            ],
        ),
        _node(
            "design_qa",
            "Design QA",
            "Score how faithfully each built screen matches its Figma frame — "
            f"gate passes at ≥{DESIGN_PASS_THRESHOLD_PCT}% of screens PASS",
            "Design QA: READ-ONLY scorer for Skill `ui-exactness` "
            "(`skills/ui-exactness/UI-Exactness.md`) — the single "
            "screen design-parity law. NEVER fixes, edits, or publishes; "
            "deviations are screen FAILs for the design-fidelity gate (fixes "
            "belong to the agent/developer re-run). Delegate to the reviewer "
            "subagent when available with DesignBrief / design-pack claim "
            "tables + app URL. PRIMARY SCORE = claim tables (a screen PASSes "
            "only when every applicable claim in its table PASSes; rollup "
            "`*-score.md` never overrides; screenshots are evidence only — "
            "the GATE rate stays screens PASS / screens total, computed from "
            "those per-screen verdicts). Apply the skill's Gates, Viewport "
            "policy, and Component-detail checklist (tables select-all + sort "
            "affordance, row states, pills, pagination, search icon, dropdown "
            "placeholder, button placement, app-wide consistency, content/data "
            "realism, MainFlow matrix, ER diagram, Figma parity both ways — "
            "missing designs authored in the session's design medium — use_figma "
            "on the option's own page, or a mockup file in the option's "
            "directory). "
            "PUBLISH THE SCREEN LIST TO THE PLAN CANVAS BEFORE SCORING: one "
            "`screen` plan item per screen under review, named, before the "
            "first screenshot — then flip each one done only when every "
            "applicable claim PASSes, and `failed` when a screen deviates (the "
            "deviation in its description). Never a single 'Score the "
            "designs' bucket item. "
            "COMPUTE "
            "THE PASS RATE = screens PASS / screens total. WRITE THE DESIGN QA "
            "REPORT: reports/design-qa-report-rev-<rev>.md — <rev> is the app's current "
            "published revision — with per-screen verdicts, claim deltas, and "
            "screenshot evidence; surface via show_file and render_pdf with the "
            "same rev-<number> suffix. Report pass_rate + reruns to the gate.",
            info=[
                "Read-only scorer: never fixes or publishes — a deviation is a screen FAIL for the design-fidelity gate",
                "Delegates to the reviewer; scores ONLY via Skill ui-exactness (claim tables SOT)",
                "Scores claim tables — claim files win over rollup scores; screenshots are evidence only",
                "Checks design parity both ways — missing designs get authored in the session's design medium (use_figma on the option's page, or a mockup file in the option's directory)",
                "Scores layout/viewport per Exactness Viewport policy — no dead space, no arbitrary max-width",
                "Lists every screen it will score on the Plan canvas before scoring, then flips each one as it lands",
                "Scores component detail: table select-all + sort affordance, row error/selected states, pill style, pagination, search icon, dropdown placeholder, button placement",
                "Checks app-wide consistency — every table shares one chrome; an odd-one-out table is a FAIL",
                "Checks content & data realism — real rows/values, no empty cells or '0 of 0' where the design is populated",
                "Checks build conventions: the MainFlow canvas is arranged as a matrix (not one long line) and the ER diagram (entities + relationships) exists",
                f"Computes screens-PASS / total and reports it for the ≥{DESIGN_PASS_THRESHOLD_PCT}% gate; FAILs loop back to the build step",
                "Writes reports/design-qa-report-rev-<n>.md + PDF with the per-screen verdicts and deviations",
            ],
        ),
        _node(
            "victory_lap",
            "Validator Victory Lap",
            "Independent double-check of the results — always runs, pass or fail",
            "Validator Victory Lap — the independent double-check. This step ALWAYS "
            "runs, pass or fail: even when the agent step failed or the gate "
            "never cleared, run it so the results get re-verified. "
            "Independently RE-VERIFY the outcome — re-drive the running app "
            "screen by screen and re-check the tenant state; don't restate "
            "earlier claims. Record what stands, what doesn't, and any "
            "discrepancies vs the validator's checklist. PUBLISH WHAT YOU WILL "
            "RE-VERIFY TO THE PLAN CANVAS FIRST — one `test` item per screen / "
            "flow / rule / story you re-drive, named with its source id, before "
            "you start; flip each one as it is re-verified. A single "
            "'Re-verify the app' bucket item hides the whole double-check from "
            "the user. WRITE THE VICTORY-LAP "
            "REPORT: reports/victory-lap-report-rev-<rev>.md — <rev> is the app's "
            "current published revision number — with the analysis: what was "
            "re-verified and how, what stands vs what doesn't, and every "
            "discrepancy against the validator's checklist. Surface it via "
            "show_file and render the PDF (render_pdf) keeping the same "
            "rev-<number> suffix. On a failed run, mark victory_lap=done once "
            "the double-check is recorded (the run status stays failed via "
            "the failed step).",
            info=[
                "Always runs — pass or fail",
                "Lists everything it will re-verify on the Plan canvas first — one item per screen, flow, rule and story",
                "Independently re-drives the app screen by screen",
                "Re-checks the tenant state against the validator's checklist",
                "Records what stands, what doesn't, and any discrepancies",
                "Writes reports/victory-lap-report-rev-<n>.md + PDF with the double-check analysis",
            ],
        ),
        _node(
            "report",
            "Implementation Report",
            "Write the implementation report & hand-off",
            "Implementation Report: write the migration report by FINISHING "
            "THE LAST INTERMEDIATE IMPLEMENTATION REPORT the validator wrote "
            "(<AppName>-r<revision>-intermediate-report.md): same skeleton, "
            "same ids, same statuses unless the victory lap overturned one "
            "(say so in the evidence), the intermediate title suffix and lead "
            "line dropped, saved as <AppName>-r<revision>-report.md. Its "
            "'REQs implemented' figure may not be LOWER than the last "
            "intermediate report's — the one the gate passed on: an item the "
            "victory lap overturned goes back through the validator gate "
            "(agent=running, validator=pending), never quietly into the final "
            "report. Cover what was "
            "built, the victory lap's verified findings, the validator's "
            "scored checklist and pass rate, remaining gaps or the failure "
            "story, and next steps. It is the post-build half of one "
            "document family with the Business Spec: the same look, the same "
            "0–9 + A section skeleton, and the same data-model, site-map and "
            "app-landscape pictures drawn the way the spec draws them, so "
            "planned and built compare box for box. The report MUST reconcile the expected "
            "requirements, business rules AND user stories one by one — one "
            "row per requirement/rule/story from the specs: its id + text · "
            "status in the reporter guide's fixed vocabulary "
            "(Implemented, tested … Not built) · tested (PASS / FAIL from the tester's TestReport "
            "— the per-item verdicts actually driven — or NOT TESTED when no "
            "verdict exists) · evidence — "
            "and, for every item not "
            "implemented or not tested, the WHY (scope decision, blocker, "
            "platform limitation — never a blank cell). EVERY spec file in "
            "the extraction input is represented: implementable slices "
            "appear with per-item statuses, meta slices (overview, "
            "non-functional, disposition, suggestions, unknowns) with at "
            "least a disposition note — a spec file with no trace in the "
            "report is a coverage bug. The report still OPENS with the "
            "page-1 KPI cards: % business requirements implemented, "
            "% business rules implemented AND tested, % user journeys PASS, "
            "and the app's AO count (Application Objects, the licensing "
            "size metric — count per the reporter guide's 'Counting AOs' "
            "and verify the current definition at "
            "https://success.outsystems.com/support/licensing/application_objects/). "
            "When gate loops happened, include the "
            "pass-rate progression across loops and reference the "
            "intermediate reports/progress-report-rev-*.md files. BEFORE "
            "delegating the report, WRITE AND RUN THE TEST EVIDENCE PACK per "
            "Skill outsystems-test-evidence-pack: scaffold it from the "
            "extraction's requirements.json (ids unchanged), write one test per "
            "flow from the TestReport's `pack` entries, each keeping the entry's "
            "`test_id` as its testId('TEST-nnn') tag unless another pack test "
            "already has that id (that test keeps it, and the new one takes the "
            "next free id check_pack.py prints), plus a signed-out @ACCESS "
            "test per screen with write or role-gated actions, mark the "
            "requirements no screen can show `untestable` with the reason, then "
            "run check_pack.py and `npm test` against the live app. A test whose "
            "result disagrees with the tester's verdict is a wrong test until "
            "the trace proves otherwise: fix the test, never weaken it to pass, "
            "and report any verdict the trace overturns. Hand the reporter the "
            "pack's evidence/summary.json and traceability matrix; its section 5 "
            "names each requirement's tests by those test ids. Delegate to the "
            "reporter subagent when available; surface the report file via "
            "show_file. Like the victory lap, this step ALWAYS runs, pass "
            "or fail.",
            info=[
                "Finishes the last intermediate Implementation Report the validator gate read: same structure, ids and statuses, made final",
                "Summarizes what was built and the victory lap's verified findings",
                "Includes the validator's scored checklist and final pass rate",
                "Reconciles every expected requirement, business rule and user story — implemented? tested? and the why when not",
                "Covers every spec file — per-item statuses for implementable slices, disposition notes for meta slices; none skipped",
                "Opens with the page-1 KPI cards — requirements %, business rules %, journeys %, and the AO count (per the OutSystems licensing definition)",
                "Shows the pass-rate progression when gate loops happened",
                "Writes and runs the Test Evidence Pack first: one Playwright test per verified flow, tagged with the spec's ids, plus the signed-out checks",
                "Lists remaining gaps and next steps; lands on the Files tab",
            ],
        ),
    ]


def _design_fidelity_gate_instructions() -> str:
    return (
        f"The gate PASSES when at least {DESIGN_PASS_THRESHOLD_PCT}% of the "
        "built screens PASS Skill `ui-exactness` claim-file scoring — a "
        "DIFFERENT metric from the validator gate (journeys). LOOP ACCOUNTING "
        "(mandatory, its OWN counter separate from the validator gate's): "
        "track this gate's reruns_used — it starts at 0 and increments by "
        "exactly 1 each time a design-fix loop completes. When you mark the "
        "design_qa step done, pass `pass_rate_pct` (the % of screens that "
        "PASS Exactness) and `reruns_used` in the update_workflow call; the "
        "tool REFUSES to advance past this gate while the pass rate is below "
        "the threshold and loops remain. The budget is exhausted ONLY when "
        f"reruns_used = {MAX_RERUNS}. Below {DESIGN_PASS_THRESHOLD_PCT}% with "
        "loops remaining you MUST loop back — 'close enough' is NOT a valid "
        "reason to skip. Fixes happen ONLY inside the agent step's re-run — "
        "design_qa stays a read-only scorer. BEFORE each loop: (a) "
        "write/refresh the design-qa report with per-screen claim verdicts, "
        "surface it via show_file; (b) set agent=running and design_qa=pending "
        "via the tool; (c) re-run the agent step scoped to ONLY the failing "
        "claim ids, then re-score. After the "
        f"{MAX_RERUNS}th completed loop, proceed with the residual per-screen "
        "gaps recorded in the report."
    )


def _migration_gates() -> list[dict]:
    return [
        _gate(
            "validator",
            f"≥{PASS_THRESHOLD_PCT}% of the validator's combined checklist (requirements, rules, journeys + implementable spec items) passing?",
            re_run_target_id="agent",
            threshold_pct=PASS_THRESHOLD_PCT,
            requirements_from_report=True,
            instructions=(
                "THE GATE READS THE INTERMEDIATE IMPLEMENTATION REPORT: when the "
                "extraction input has a requirements.json, the tool computes the "
                "'REQs implemented' figure (the spec ids whose appendix-Z row answers "
                "Implemented Yes, over every spec id; IN-nn/CAP-nn rows don't count; "
                "the page-1 card) of the latest "
                f"<AppName>-r<revision>{INTERMEDIATE_REPORT_SUFFIX} itself, and the "
                "gate's pass rate is the LOWER of that figure and the "
                "`pass_rate_pct` you report — so a report reading 5% can never "
                "follow a passed gate. It refuses to advance while that report "
                "is missing or fails the id check. "
                f"The gate PASSES when at least {PASS_THRESHOLD_PCT}% of the "
                "validator's COMBINED CHECKLIST is PASS — the SAME denominator "
                "the validator computes, not a subset: business requirements, "
                "business rules and user journeys (one item each), PLUS the "
                "swept implementable spec items (every entity/attribute, screen, "
                "role/access rule, workflow/process, integration). Verdict "
                "accounting, stated once so pass rates are reproducible: PASS "
                "counts toward the numerator; FAIL, NOT TESTED and PARTIAL count "
                "as NOT a pass (a PARTIAL is never rounded up — its undriven "
                "criterion keeps the item out of the numerator); NOT OBSERVABLE "
                "is excluded from the denominator entirely. An item is scored by "
                "its CATEGORY, not its file: a role/access, data-model, rule, "
                "story or screen requirement is on the checklist even when it "
                "lives in a meta-slice file (e.g. an access-control rule filed "
                "under 09-non-functional.md is scored). Only genuinely meta "
                "content — narrative overview, migration-disposition, "
                "agentic-suggestions, unknowns, and non-functional ASPIRATIONS "
                "with no observable behaviour — adds no items. "
                "LOOP ACCOUNTING (mandatory): track reruns_used — it starts at "
                "0 and increments by exactly 1 each time a re-run loop "
                "completes. Whenever you mark the validator step done, include "
                "`pass_rate_pct` and `reruns_used` in the update_workflow "
                "call; the tool REFUSES to advance past a failed gate while "
                "loops remain. The re-run budget is exhausted ONLY when "
                f"reruns_used = {MAX_RERUNS}. Below the threshold with loops "
                "remaining you MUST loop back — skipping the loop for any "
                "other reason (effort already spent, diminishing returns, "
                '"solid attempts made") violates the workflow. Fixes happen '
                "ONLY inside the agent step's re-run — never in the "
                "validator, which stays a read-only scorer. BEFORE each "
                "loop: (a) write an INTERMEDIATE PROGRESS REPORT — "
                "reports/progress-report-rev-<reruns_used+1>.md with the validator's "
                "scored checklist, the pass rate, what failed, and the scope "
                "of the upcoming re-run — and surface it via show_file so it "
                "lands on the Files tab; (b) set agent=running and "
                "validator=pending via the tool; (c) re-run the agent step "
                f"scoped to ONLY the failing items. After the {MAX_RERUNS}th "
                "completed loop, proceed to the report step regardless — the "
                "remaining gaps get recorded in the final victory-lap report."
            ),
        ),
        _gate(
            "design_qa",
            f"≥{DESIGN_PASS_THRESHOLD_PCT}% of screens matching their Figma "
            "design (visual + component detail)?",
            re_run_target_id="agent",
            threshold_pct=DESIGN_PASS_THRESHOLD_PCT,
            instructions=_design_fidelity_gate_instructions(),
        ),
    ]


_MIGRATION_PREAMBLE = """This workflow migrates a {source} application to OutSystems starting at the
Agent step: extraction is NOT part of the run. The extraction output must
already be available in this conversation — analysis documents, specs, the
legacy source itself (attached files or an uploaded source folder), prior
analysis, or a design handoff such as a Figma URL in the instructions (read
it via the Figma tools; its screens and flows define the business
requirements and user journeys). If NO such input exists, call
`mcp__workflow__update_workflow` with the agent node marked `failed`, tell
the user exactly what to attach, and stop.

The spec files ARE the run's contract. Enumerate EVERY spec file in the
extraction input — for an extractor-generated collection that means all
13 domain slices (`00-overview.md` … `12-unknowns.md`) plus
`requirements.json` and the Business Spec; for ad-hoc input, every
attached spec/analysis doc — and read each one: every individually-
identified item they define (entities and attributes, screens, roles
and access rules, business rules, workflows/processes, user stories,
logic/services, integrations) must end up implemented in the app or
explicitly accounted for as a recorded gap. Meta slices (00-overview,
09-non-functional, 10-migration-disposition, 11-agentic-suggestions,
12-unknowns) are context and disposition records, not per-item build
scope: honor dropped/deferred dispositions and surface unknowns as open
questions — only the implementable slices feed the checklist and the
gate denominator. Two sources get per-item
drive-testing. LOCATE THE BUSINESS-RULES SOURCE among the extraction
input: the
extractor's `04-business-rules.md` slice, any other file carrying the
rules (e.g. a `business-rules.md`, the rules section of the Business
Spec or of the modernized spec — Glob for it, don't assume the name),
and the rule entries in `requirements.json`. Do the same for the
USER-STORIES SOURCE: the extractor's `06-user-stories.md` slice, any
other file carrying the stories (e.g. a `user-stories.md`), and the
story entries in `requirements.json`. When such a source exists, every
individually-identified rule and story is part of the run's contract:
the agent step implements it, the validator tests it one by one, and
the implementation report reconciles each one — implemented? tested?
and the why when either is missing.

The Plan canvas is the run's working memory — keep it at ITEM granularity.
Every plan any step emits carries ONE ITEM PER INDIVIDUALLY-IDENTIFIED THING:
one per requirement, business rule, user story, screen, entity, relationship,
seeded entity, action, error path and test — titled with the item's source id
where the specs number them (e.g. "BR-07 — Overdue loans block new
checkouts"). A bucket item that stands for many ("Revisit business
requirements", "Revisit user journeys", "Implement the business rules", "Test
the app") is a bug: it hides an unknown amount of work behind one checkbox,
and work that is not its own item is work the run forgets. A 60-item plan is
the correct plan — the canvas scrolls and each section collapses behind its
own done/total counter. In particular, before ANY testing or scoring step
starts driving the app, the individual checks it is about to run must already
be listed on the canvas by name.

Design tooling: whenever a step creates or revises a UI design, author it
directly in Figma with the `use_figma` MCP tool (prefer it over any other
generation path), and put each design option on its OWN Figma page — never
stack designs on one canvas. Do NOT generate HTML mockups as the design
deliverable; only produce HTML when the user has explicitly asked for it."""


def _workflow(
    wf_id: str,
    source: str,
    label: str,
    *,
    coming_soon: bool = False,
    description: str | None = None,
    nodes: list[dict] | None = None,
    gates: list[dict] | None = None,
    preamble: str | None = None,
) -> dict:
    wf = {
        "id": wf_id,
        "command": f"/{wf_id}",
        "label": label,
        "description": description
        or (
            f"Generate an OutSystems app from a {source} extraction, "
            "validate coverage, and produce the implementation report."
        ),
        "source": source,
        "nodes": nodes if nodes is not None else _migration_nodes(source),
        "gates": gates if gates is not None else _migration_gates(),
        "preamble": (preamble or _MIGRATION_PREAMBLE).format(source=source),
    }
    if coming_soon:
        wf["comingSoon"] = True
    return wf


# --- /extract-requirements --------------------------------------------------
# Runs the extraction pipeline (Notes, AB Suite, MS Access, AS/400 (DDS, RPG
# and CL source), AS/400 with CA 2E / Synon, COBOL, Java, .NET and Node.js behind one parser per stack) on the attached legacy sources via the mcp__extractor__*
# tools. Upstream of the migration workflow: its published spec collection is
# exactly the extraction input /workflow-legacy-app asks for.

_EXTRACT_PREAMBLE = """This workflow extracts requirements from a legacy application's sources and
publishes a modernization spec collection: the canonical 13 domain slices,
manifest.json, a REQ-keyed requirements.json backlog, and a combined
Business Spec. The legacy sources must already be in this conversation —
attached files (e.g. a Notes .dxl export, an AB Suite .pmodel export, an MS
Access database, AS/400 DDS, RPG and CL source members, a CA 2E / Synon model
export with its AS/400 members, COBOL copybooks, or Java, .NET or Node.js code) or an uploaded source folder. If NO such input exists, call
`mcp__workflow__update_workflow` with the detect node marked `failed`, tell
the user exactly what to attach, and stop.

Ground rules: drive the pipeline ONLY through the `mcp__extractor__*` tools
(never reimplement parsing yourself), always pass ABSOLUTE paths, write
output under `generated-specs` inside your working directory, and derive a
PascalCase customer name from the app/file name unless the user gave one.
AWS Transform is off on the extraction service, so all nine stacks run on
the extractor's own parsers. Notes (.dxl), AB Suite (.pmodel), MS Access, AS/400
(DDS, RPG and CL source) and AS/400 with a CA 2E / Synon model export run
from raw sources, with you
authoring the enrichment. COBOL, Java, .NET and Node.js raw code get standard
analysis: the extractor's own parsers plus the LLM. There is no engine to
pick: never ask the user for AWS credentials and never offer AWS Transform
as a fix. Read `analysis` on every result: `standard` means standard
analysis wrote the spec, and `analysis_complete: true` means it read every
program with nothing skipped, so the spec is complete. When `analysis` is
`standard` and `analysis_complete` is not true, the spec is structural and
incomplete: say so plainly in the report and name the causes listed in
`analysis_incomplete` (on the result when it carries them, otherwise in the
published `manifest.json`).
Supported stacks: Notes (.dxl), AB Suite (.pmodel exports), MS Access,
AS/400 (DDS, RPG and CL source), AS/400 with CA 2E / Synon model exports,
COBOL, Java, .NET and Node.js.

WHAT THE BUSINESS SPEC IS. The Business Spec (`<Customer>-Business-Spec.md`)
is the human-friendly consolidation of the 13 domain slices — the same
requirements a business reader can absorb in one pass instead of reading
thirteen files. It is a WHAT document: what the system is expected to do,
in the customer's own vocabulary — business requirements, business rules,
user journeys/stories, the meaning of the data, roles and who may do what,
the processes the business runs.

It MUST NOT contain implementation work. No OutSystems/ODC constructs
(entities, attributes-as-columns, aggregates, screens-as-OML-artifacts,
server/client actions, blocks, timers, themes), no technology or
architecture choices, no code or pseudo-code, no build steps, no migration
plan / phases / sequencing / effort / estimates, and no statements about
what an agent or team will do next. The ONE exception is the extractor's
labelled "Recommended migration" section, a suggestion for the business to
review: everything inside it is allowed (the suggested apps, waves, the apps
diagram, libraries, asset kinds, user groups, a size table, the first go-live
and risks); the same content anywhere else is leakage. "The system must block
a checkout while a loan is overdue" belongs; "add an IsOverdue attribute and
validate it in the CheckoutBook server action" does not. Implementation-flavoured slices
(`10-migration-disposition.md`, `11-agentic-suggestions.md`) stay OUT of
it — they are separate artifacts and keep their own files.

The Business Spec is authored by the extractor pipeline, so implementation
leakage is a finding you REPORT (and gate on at the review step), not
something you silently rewrite: say which sections leaked and what they
leaked, and note that the durable fix belongs in the extractor's Business
Spec generation, not in a post-hoc edit here."""

_EXTRACT_NODES = [
    _node(
        "detect",
        "Detect",
        "Locate the attached legacy sources and detect the stack",
        "Locate the legacy source input: look for attached files in your "
        "working directory and any uploaded source folder mentioned in the "
        "conversation. Then call `mcp__extractor__detect_source` with the "
        "ABSOLUTE path (pass the most specific path that holds ONE app's "
        "sources — a single .dxl file, a source tree root). A backend with "
        "its own front end is one app and one run: pass the directory that "
        "holds both and don't split it, and don't re-run to get a longer "
        "screen list. Detection picks the backend stack for that tree, so "
        "pass `source: auto` to `run_extraction` and don't override "
        "`source` to force the front-end stack. A front end in a separate repo is not covered by "
        "one run: say so and ask the user what to attach. Don't guess. "
        "When the backend was detected, don't wait on the answer: mark this "
        "node done, run the backend alone, and name the missing front end as "
        "a gap in the report. Attaching it later means a new run on one "
        "directory that holds both. "
        "If detection "
        "is ambiguous or nothing is found, mark this node failed and tell "
        "the user exactly what to attach.",
        info=[
            "Scans the conversation's attached files and uploaded source folders",
            "Auto-detects the stack: Notes (.dxl), AB Suite, MS Access, AS/400 (DDS, RPG and CL source), AS/400 CA 2E, COBOL, Java, .NET or Node.js",
            "Asks for the right input when nothing usable is attached",
        ],
    ),
    _node(
        "extract",
        "Extract",
        "Run the extraction pipeline (enriched when the stack allows it)",
        "Run `mcp__extractor__run_extraction` with the detected source, an "
        "ABSOLUTE `out` under your working directory (e.g. <cwd>/generated-specs) "
        "and the customer name. Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL "
        "source) and AS/400 with CA 2E / Synon default to the TWO-PHASE agent "
        "enrichment: the first call returns status=enrichment_required with an "
        "enrichment-request.json — read it, author the enrichment-response.json "
        "it asks for STRICTLY from the request's facts (follow its "
        "response_schema exactly; never invent entities, screens or rules the "
        "facts don't support), then call run_extraction again with "
        "`enrichment_response` set. If the response is rejected twice, fall "
        "back to deterministic=true and note the downgrade in the report. "
        "COBOL/JAVA/NODE/DOTNET: call run_extraction with `path` at the RAW "
        "source tree and the source (cobol|java|node|dotnet). The service runs "
        "standard analysis (its own parsers plus the LLM), authors the 13 domain "
        "slices, then refine/gate/render/publish. There is NO engine flag and NO "
        "agent-authored rerun: calling it again with slices you wrote yourself "
        "takes the same path and gets the same result. If the run comes back "
        "with `budget_exhausted: true` (the analysis hit its cap) or "
        "`stack_not_enabled`, do NOT retry it: record the shortfall, say plainly "
        "that no spec collection was produced for this stack, and go to the "
        "report. READ `analysis` ON EVERY RESULT: `analysis: standard` with "
        "`analysis_complete: true` is a complete standard-analysis spec. "
        "`analysis: standard` without `analysis_complete: true` is a STRUCTURAL, "
        "incomplete spec even with status=succeeded: carry it on to review and "
        "report, name the causes from `analysis_incomplete` (on the result when "
        "it carries them, otherwise in the published `manifest.json`), never "
        "present it as complete, and don't "
        "re-run it (it takes the same path).",
        info=[
            "Runs the unified extraction pipeline (one parser per stack)",
            "Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL source) and AS/400 with CA 2E: agent-in-the-loop enrichment, the agent authors the semantic layer from parsed facts",
            "COBOL, Java, .NET and Node.js: standard analysis (own parsers plus the LLM), no engine flag and no AWS credentials; an incomplete analysis is reported with its causes",
            "Publishes generated-specs/<Customer>/v1, v2, … on each run",
        ],
    ),
    _node(
        "review",
        "Review",
        "Verify the published artifacts and quality gates",
        "Review the published version directory: verify the 13 domain slices, "
        "manifest.json, requirements.json and the Business Spec exist and are "
        "non-empty; read manifest.json and requirements.json and sanity-check "
        "them against the source input (entity/screen names really come from "
        "the sources). READ THE BUSINESS SPEC AND CHECK IT IS BUSINESS-ONLY: "
        "it is the human-friendly version of the 13 slices and must state only "
        "WHAT is expected — requirements, rules, journeys, data meaning, roles, "
        "processes — with NO implementation work in it (no OutSystems/ODC "
        "constructs, no technology or architecture choices, no code, no build "
        "steps, no migration plan / phases / effort, no 'what we will do next'; "
        "the ONE exception is the extractor's labelled 'Recommended migration' "
        "section, a suggestion to review: everything inside it is allowed "
        "(e.g. the suggested apps, waves, the apps diagram, libraries, asset "
        "kinds, user groups, a size table, the first go-live and risks); the "
        "same content anywhere else is leakage; "
        "migration-disposition and agentic-suggestions content stays in its own "
        "slices). Every main Business Spec should carry that 'Recommended "
        "migration' section, whatever the number of domains (the per-domain "
        "and application-wide reports don't). A missing section is a RECORDED "
        "FINDING, not a failing check: the spec came from an extractor that "
        "predates the section and a re-run can't add it, so leave it out of the "
        "pass rate, never loop back to Extract for it, and name it in the report "
        "with the durable fix in the extractor. It comes in one of two "
        "forms, both valid: the ordered plan (apps, waves, the apps diagram) "
        "when enough domains link, or a short form that says to migrate it as "
        "one app, followed by the other OutSystems assets to consider "
        "(libraries, workflows, AI agents). "
        "Any implementation leakage is a FAILING check at this gate: "
        "name the section and the leaked content, and record that the durable "
        "fix is in the extractor's Business Spec generation. "
        "Treat the run status as the gate signal: "
        "status=succeeded means the pipeline's own gates are green; "
        "gates_failed means they are not — report the result's "
        "`failed_checks` when present, and otherwise say that which checks "
        "failed is not available (the gate reports stay with the service, so "
        "don't look for them in the spec). Gates are not the whole story: a "
        "result with `analysis: standard` and `analysis_complete` not `true`, "
        "a degraded run (a non-empty `analysis_incomplete` list, whatever "
        "`analysis` says: the extractor never sends it on a complete run), or "
        "a run whose warnings say \"Do not report this run as a complete spec\" "
        "(the sentence the extractor ends each incomplete-run warning with) "
        "is an INCOMPLETE spec even when its gates are green: record it as a "
        "failing check here, saying the spec is structural (standard analysis "
        "did not read every program) or degraded, naming the causes and "
        "quoting each warning. An incomplete spec never passes the gate, "
        "whatever the pass rate. Any other warning is quoted in the report and "
        "fails no check. A standard result with `analysis_complete: "
        "true` and no such warning is complete and passes this check. "
        "Compute the pass rate as the "
        "percentage of these checks passing and report it at the gate.",
        info=[
            "Checks all 13 slices + manifest.json + requirements.json + Business Spec are present and non-empty",
            "Checks the Business Spec reads as business-only — the human-friendly version of the 13 slices, stating WHAT is expected with no implementation work, technology choices, code or migration plan in it (except the extractor's labelled Recommended migration section)",
            "Checks every main Business Spec carries the Recommended migration (the ordered plan, or 'migrate it as one app' with the other OutSystems assets to consider); a missing one is a recorded finding, not a re-run",
            "Cross-checks manifest domains and REQ backlog entries against the actual sources",
            "Reads the run's gate status and failed_checks; green gates required to pass",
            "Flags an incomplete standard analysis, a degraded run or the extractor's 'Do not report this run as a complete spec' warning as incomplete, even with green gates; other warnings are quoted only",
        ],
    ),
    _node(
        "report",
        "Report",
        "Publish the spec collection to the canvas and summarize",
        "When the source has a front end, compare its routes with the screens "
        "in `02-screens.md` and `requirements.json`. If the spec has no "
        "screens, or far fewer than the front end's routes, say so in the "
        "report: name the framework and roughly how many routes you see in "
        "the source, and say that a build from this spec with "
        "`/workflow-legacy-app` will be missing those screens. Don't split "
        "the source and don't re-run: neither gives a longer screen list. "
        "When the front end is in a separate repo that wasn't attached, say "
        "so too: the spec has none of its screens, and a build from this spec "
        "will be missing them. "
        "Publish the ENTIRE published version directory to the canvas Files "
        "tab: call `mcp__preview__show_file` once for EVERY file the run "
        "produced — the Business Spec (`.md`) first, then all 13 "
        "domain slices (`00-overview.md` … `12-unknowns.md`), then "
        "`manifest.json`, `requirements.json`, and `pipeline-events.jsonl`. "
        "Do not stop at a subset; the user must see every artifact. Then "
        "summarize in chat: detected stack, customer, version dir, domain "
        "count, REQ counts per tier, gate status (with `failed_checks` on "
        "gates_failed), the analysis depth, every warning, and any enrichment "
        "downgrade or capped/refused run (`budget_exhausted`, `stack_not_enabled`), and every "
        "recorded finding (a main Business Spec without the Recommended "
        "migration section, with the fix in the extractor). "
        "When the spec is incomplete (`analysis: standard` without "
        "`analysis_complete: true`, a non-empty `analysis_incomplete` list "
        "whatever `analysis` says, or a warning that says \"Do not report "
        "this run as a complete spec\"), lead the report with it, before the "
        "summary, right after the `gates_failed` verdict when the run has "
        "one: say the spec is INCOMPLETE (structural for a standard "
        "analysis, degraded otherwise), name the causes from "
        "`analysis_incomplete`, quote every warning, and say "
        "/workflow-legacy-app will be building from an incomplete spec. Close by pointing the user "
        "at /workflow-legacy-app to generate the OutSystems app from this "
        "extraction.",
        info=[
            "When the source has a front end, compares its routes with 02-screens.md and requirements.json and names a screen shortfall in the report",
            "Publishes EVERY produced file (Business Spec .md, all 13 slices, manifest.json, requirements.json, pipeline-events.jsonl) to the Files canvas",
            "Summarizes domains, requirements backlog, gate status and analysis depth",
            "Calls out an incomplete standard-analysis spec as structural and names its causes",
            "Hands off to /workflow-legacy-app — the extraction output is its input",
        ],
    ),
]

_EXTRACT_GATES = [
    _gate(
        "review",
        f"Artifacts complete + extractor gates green (≥{PASS_THRESHOLD_PCT}%)?",
        re_run_target_id="extract",
        instructions="Gate: pass when the review's artifact/gate checklist "
        f"passes at ≥{PASS_THRESHOLD_PCT}% AND the run status is `succeeded` "
        "AND the spec is not incomplete (an incomplete spec never passes, "
        "whatever it scores). "
        "On FAIL, loop back to the Extract step (fix the input path, re-author "
        "the enrichment response, or fall back to deterministic mode) and "
        "re-run; record pass_rate_pct and reruns_used on every gate crossing. "
        "If the extract result carried `budget_exhausted: true` or "
        "`stack_not_enabled`, don't repeat the run (it takes the same path): "
        "stop looping and proceed to the report with the shortfall recorded. "
        "The same goes for an incomplete spec (`analysis: standard` without "
        "`analysis_complete: true`, a non-empty `analysis_incomplete` list "
        "whatever `analysis` says, or a warning that says \"Do not report "
        "this run as a complete spec\"): it never counts as a pass, and a re-run "
        "takes the same path, so don't loop on it. Go to the report and lead "
        "with it. A main "
        "Business Spec without the 'Recommended migration' section is a recorded "
        "finding, not a failing check: it is not in the pass rate and is never a "
        "reason to loop.",
        threshold_pct=PASS_THRESHOLD_PCT,
    ),
]


# Two launchable workflows: extraction (any stack, auto-detected), and the
# generic legacy migration it hands off to.
# The per-stack /legacy-migrate-* comingSoon placeholders were removed once
# /extract-requirements covered the per-technology story.
WORKFLOWS: dict[str, dict] = {
    w["id"]: w
    for w in (
        _workflow("workflow-legacy-app", "legacy", "Migrate a legacy app → OutSystems"),
        _workflow(
            "extract-requirements",
            "legacy",
            "Extract requirements from legacy sources",
            description=(
                "Run the extraction pipeline on attached sources "
                "(Notes, AB Suite, MS Access, AS/400 (DDS, RPG and CL source), "
                "AS/400 with CA 2E / Synon, COBOL, Java, "
                ".NET or Node.js, auto-detected) and publish "
                "the modernization spec collection."
            ),
            nodes=_EXTRACT_NODES,
            gates=_EXTRACT_GATES,
            preamble=_EXTRACT_PREAMBLE,
        ),
    )
}

# The command unknown workflow tokens are pointed at in the catalog reply.
DEFAULT_WORKFLOW_COMMAND = WORKFLOWS["workflow-legacy-app"]["command"]


def workflow_catalog() -> list[dict]:
    """The composer-autocomplete view of the registry: command + labels only."""
    return [
        {
            "command": w["command"],
            "label": w["label"],
            "description": w["description"],
            "comingSoon": bool(w.get("comingSoon")),
        }
        for w in WORKFLOWS.values()
    ]


def match_workflow_command(content: str) -> tuple[str, str] | None:
    """Split a chat message into (leading workflow-command token, remaining text).

    Returns None when the message doesn't start with a workflow prefix, so
    ordinary chat (including other ``/``-leading text) is never intercepted.
    The token match is case-sensitive by convention (commands are lowercase).
    """
    stripped = content.strip()
    if not stripped.startswith(WORKFLOW_COMMAND_PREFIXES):
        return None
    parts = stripped.split(None, 1)
    token = parts[0]
    extra = parts[1].strip() if len(parts) > 1 else ""
    return token, extra


def workflow_nodes(workflow: dict, statuses: dict[str, str] | None = None) -> list[dict]:
    """The workflow's full node list (public fields) with statuses merged in."""
    statuses = statuses or {}
    nodes = []
    for spec in workflow["nodes"]:
        status = str(statuses.get(spec["id"], "pending"))
        if status not in WORKFLOW_NODE_STATUSES:
            status = "pending"
        node = {
            "id": spec["id"],
            "title": spec["title"],
            "description": spec["description"],
            "status": status,
        }
        # The step's main tasks/validations, shown behind the node card's
        # info icon — the curated bullets when authored, else the step's
        # prompt instructions so custom workflows still get a popover.
        info = spec.get("info") or ([spec["instructions"]] if spec.get("instructions") else [])
        if info:
            node["info"] = list(info)
        nodes.append(node)
    return nodes


def _public_gates(workflow: dict) -> list[dict]:
    """The gates as sent to the frontend — the prompt-side fields stripped."""
    return [{k: v for k, v in g.items() if k not in _GATE_PROMPT_FIELDS} for g in workflow["gates"]]


def _crossed_thresholded_gate(workflow: dict, statuses: dict[str, str]) -> dict | None:
    """The thresholded gate at the current frontier the statuses are crossing.

    "Crossing" = the gate's anchor node has REACHED A VERDICT (done or failed)
    AND some node after the anchor is running/done — i.e. the run is advancing
    past the gate decision.

    `failed` counts, and that is the whole point: requiring `done` meant a run
    could skip the loop budget entirely by reporting the anchor step as failed
    instead. A live run did exactly that — validator at 22% against the
    95% gate, `loops 0/5`, and because the step was `failed` no gate was
    detected, no accounting was demanded, and it advanced to design QA and the
    report untouched. Failing the step a gate anchors is not a way past the
    gate; it is the case the gate exists for. (A failed anchor with nothing
    after it running is a legitimately stopped run and still matches nothing.)

    With
    more than one thresholded gate (functional validator, then design fidelity)
    the run can be past several anchors at once; return the MOST ADVANCED such
    gate (the one nearest the running frontier), because that's the decision
    being made right now and the one the reported pass_rate/reruns describe. A
    run looping on the earlier gate hasn't reached the later gate's anchor yet,
    so only the earlier one matches — the accounting stays unambiguous.
    """
    node_order = [n["id"] for n in workflow["nodes"]]
    crossed: dict | None = None
    best_anchor_idx = -1
    for gate in workflow["gates"]:
        if "thresholdPct" not in gate:
            continue
        anchor = gate["afterNodeId"]
        if anchor not in node_order or statuses.get(anchor) not in ("done", "failed"):
            continue
        anchor_idx = node_order.index(anchor)
        later = node_order[anchor_idx + 1 :]
        # `failed` counts on THIS side too. Treating only running/done as
        # advancement left the mirror image of the anchor hole above: cross the
        # gate and mark the first post-anchor step `failed` in the same call, and
        # the run has demonstrably advanced while matching no gate — so the loop
        # budget is skipped exactly as it was by failing the anchor.
        if any(statuses.get(nid) in ("running", "done", "failed") for nid in later):
            if anchor_idx > best_anchor_idx:
                best_anchor_idx = anchor_idx
                crossed = gate
    return crossed


def gate_reads_report(workflow: dict, statuses: dict[str, str]) -> bool:
    """True when the gate these statuses cross takes its pass rate from the intermediate report."""
    gate = _crossed_thresholded_gate(workflow, statuses)
    return bool(gate and gate.get("requirementsFromReport"))


def report_figure_pct(report_figure: dict | None) -> float | None:
    """The percentage of a host's report reading, or None when it carries none (no figure, an error, a bad shape)."""
    if not report_figure or report_figure.get("error"):
        return None
    try:
        return float(report_figure["pct"])
    except (KeyError, TypeError, ValueError):
        return None


def gate_pass_rate(pass_rate_pct: object, report_figure: dict | None) -> object:
    """The pass rate a gate decides on and the canvas shows: the lower of the reported one and the report's figure."""
    figure = report_figure_pct(report_figure)
    if figure is None:
        return pass_rate_pct
    try:
        reported = None if pass_rate_pct is None else float(pass_rate_pct)
    except (TypeError, ValueError):
        reported = None
    return figure if reported is None else min(reported, figure)


def status_coherence_violation(workflow: dict, statuses: dict[str, str]) -> str | None:
    """Why this reported status set cannot describe a real run.

    These pipelines are linear — one step at a time, with gates modelling the
    loops — so two of the accounting rules the refusal text already states are
    checkable directly, and were not being checked:

    * only ONE node may be `running`;
    * nothing AFTER the running node may still be `done`/`failed`, because a
      loop-back re-runs everything downstream ("re-call update_workflow with
      `<target>=running and every later step pending`").

    Seen in production the first time a gate refusal actually forced a loop: the
    agent re-wired the target to `running` but left the anchor `running` too and
    the already-passed `design_qa` on `done`, so the canvas drew two steps in
    flight at once and painted the same sub-progress under both (the frontend
    shows plan progress under ANY running node). The graph is the run's memory,
    so a half-applied loop is not cosmetic: the next gate reads it.

    Returns None when the set is coherent.
    """
    order = [n["id"] for n in workflow["nodes"]]
    known = {nid: statuses.get(nid) for nid in order}
    running = [nid for nid in order if known.get(nid) == "running"]
    if len(running) > 1:
        return (
            "STATUS REJECTED: "
            + ", ".join(f"'{nid}'" for nid in running)
            + " are all marked running, but this pipeline runs ONE step at a "
            "time — a loop back to an earlier step ends the later one. Re-call "
            "update_workflow with only the step you are actually running set "
            "to running, and every step after it pending."
        )
    if running:
        after = order[order.index(running[0]) + 1 :]
        stale = [nid for nid in after if known.get(nid) in ("done", "failed")]
        if stale:
            return (
                f"STATUS REJECTED: '{running[0]}' is running again, so "
                + ", ".join(f"'{nid}'" for nid in stale)
                + " cannot still be "
                + ("done" if known.get(stale[0]) == "done" else "failed")
                + " — a re-run invalidates every result downstream of it. "
                "Re-call update_workflow with those steps pending; they earn "
                "their status back when they re-run."
            )
    return None


def gate_accounting_violation(
    workflow: dict,
    statuses: dict[str, str],
    pass_rate_pct: float | None,
    reruns_used: int | None,
    report_figure: dict | None = None,
) -> str | None:
    """Why this update_workflow call may NOT advance past a thresholded gate.

    ``report_figure`` is the host's reading of the intermediate Implementation
    Report for a gate marked ``requirementsFromReport`` (see
    ``gate_reads_report``): ``{"done": X, "total": N, "pct": P, "path": ...}``
    (``check_report_ids.implemented_figure``), or ``{"error": why}`` when the
    report is missing or fails the id check. None means there is no spec
    ``requirements.json`` to count against, and the gate keeps the reported pass
    rate alone. With a figure, the pass rate is the lower of the two.

    Returns the refusal message when the reported statuses cross a thresholded
    gate that (a) is missing its pass-rate accounting, or (b) failed with
    re-run loops still in budget — the exact hole a run once slipped through
    by claiming "re-run budget exhausted" at 0 loops used. Returns None when
    no thresholded gate is being crossed, the gate passed, or the budget is
    genuinely spent.
    """
    gate = _crossed_thresholded_gate(workflow, statuses)
    if gate is None:
        return None
    threshold = gate["thresholdPct"]
    max_reruns = gate.get("maxReruns", MAX_RERUNS)
    anchor = gate["afterNodeId"]
    # The model may send numbers as strings; unparseable == not reported.
    try:
        pass_rate_pct = None if pass_rate_pct is None else float(pass_rate_pct)
    except (TypeError, ValueError):
        pass_rate_pct = None
    try:
        reruns_used = None if reruns_used is None else int(reruns_used)
    except (TypeError, ValueError):
        reruns_used = None
    if pass_rate_pct is None:
        return (
            f"GATE BLOCKED: you are advancing past the '{gate['label']}' gate "
            "without reporting its accounting. Re-call update_workflow with "
            "`pass_rate_pct` (the scored pass rate for this gate) and "
            "`reruns_used` (this gate's completed re-run loops, starts at 0)."
        )
    from_report = ""
    if gate.get("requirementsFromReport") and report_figure is not None:
        if report_figure.get("error"):
            return (
                f"GATE BLOCKED: the '{gate['label']}' gate reads its pass rate from the "
                f"intermediate Implementation Report (<AppName>-r<revision>{INTERMEDIATE_REPORT_SUFFIX}), "
                f"and {report_figure['error']}. Resolve that first: a missing or failing report is "
                "written or fixed (the final report's skeleton, ids and KPI cards, from this scoring); "
                "any other cause is fixed where the message says. Then re-call update_workflow."
            )
        figure = report_figure_pct(report_figure)
        if figure is None:
            return (
                f"GATE BLOCKED: the '{gate['label']}' gate reads its pass rate from the "
                f"intermediate Implementation Report (<AppName>-r<revision>{INTERMEDIATE_REPORT_SUFFIX}), "
                "and the host read no requirements figure from it. Re-check the report with "
                "check_report_ids.py, then re-call update_workflow."
            )
        if figure < pass_rate_pct:
            pass_rate_pct = figure
            from_report = (
                f" (the intermediate report's REQs implemented: {report_figure['done']} of "
                f"{report_figure['total']} spec ids, lower than the pass rate you reported)"
            )
    used = int(reruns_used or 0)
    if pass_rate_pct >= threshold or used >= max_reruns:
        return None
    target = gate.get("reRunTargetId", workflow["nodes"][0]["id"])
    loop_prep = gate.get("loopPrep") or (
        f"write reports/progress-report-rev-{used + 1}.md with the scored checklist and "
        "surface it via show_file"
    )
    # A gate whose re-run target IS its own anchor (the step redoes its own
    # work) can't be told to set that step running AND pending in one call.
    re_wire = (
        f"{target}=running and every later step pending"
        if target == anchor
        else f"{target}=running and the '{anchor}' step pending"
    )
    return (
        f"GATE BLOCKED: pass rate {pass_rate_pct:g}%{from_report} is below the "
        f"{threshold}% '{gate['label']}' gate and only {used} of {max_reruns} "
        f"re-run loops are used — the budget is exhausted ONLY at {max_reruns} "
        "completed loops; there is no other justification for skipping the "
        f"loop. Do this instead: (1) {loop_prep}; (2) re-call "
        f"update_workflow with {re_wire}, and reruns_used={used}; "
        f"(3) re-run the {target} step scoped "
        "to ONLY the failing items, then re-score and report "
        f"reruns_used={used + 1}."
    )


def build_workflow_event(
    workflow: dict,
    statuses: dict[str, str] | None = None,
    note: str = "",
    gate_outcome: dict | None = None,
) -> dict:
    """The ``update_workflow`` WebSocket payload for one full run state.

    Every event carries the complete graph (nodes + gates + progress) so the
    frontend just replaces its run state — no client-side merging, and a
    single persisted event restores the canvas after a reload.

    ``gate_outcome`` = {"passRatePct": float, "rerunsUsed": int} as reported
    by the agent — attached to the (first) thresholded gate so the canvas
    shows the score and loop budget on the diamond.
    """
    nodes = workflow_nodes(workflow, statuses)
    done = sum(1 for n in nodes if n["status"] == "done")
    if any(n["status"] == "failed" for n in nodes):
        run_status = "failed"
    elif done == len(nodes):
        run_status = "done"
    else:
        run_status = "running"
    current = next((n["id"] for n in nodes if n["status"] == "running"), None)
    gates = _public_gates(workflow)
    if gate_outcome and gate_outcome.get("passRatePct") is not None:
        # Attach the reported score to the thresholded gate currently being
        # crossed (so a two-gate run shows the design-fidelity score on the
        # design diamond, not the validator's); fall back to the first
        # thresholded gate when no crossing is in progress yet.
        crossed = _crossed_thresholded_gate(workflow, statuses or {})
        crossed_after = crossed["afterNodeId"] if crossed else None
        for g in gates:
            if "thresholdPct" not in g:
                continue
            if crossed_after is None or g["afterNodeId"] == crossed_after:
                g["outcome"] = {
                    "passRatePct": gate_outcome["passRatePct"],
                    "rerunsUsed": int(gate_outcome.get("rerunsUsed") or 0),
                    "maxReruns": g.get("maxReruns", MAX_RERUNS),
                }
                break
    run: dict = {
        "id": workflow["id"],
        "command": workflow["command"],
        "label": workflow["label"],
        "status": run_status,
        "nodes": nodes,
        "gates": gates,
        "progress": {"done": done, "total": len(nodes)},
    }
    if current:
        run["currentNode"] = current
    if note:
        run["note"] = note
    return {"type": "update_workflow", "workflow": run}


# Shown on a run the turn abandoned. Names the cause the user can act on
# (re-run) rather than implying the pipeline itself rejected something.
STALLED_NOTE = (
    "The turn ended while this run was still in flight, so it never reported back. "
    "Nothing is working on it now — re-run the command to continue."
)


def sweep_stalled_run(run: dict) -> dict | None:
    """The terminal ``update_workflow`` payload for a run abandoned mid-flight.

    Returns None when there is nothing to correct — the run is already terminal
    (``done``/``failed``), or its id is not in the registry.

    The card is entirely agent-driven: ``mcp__workflow__update_workflow`` flips
    node statuses and nothing else ever touches it. So a turn that announces a
    workflow, marks its first node ``running`` and then ends — interrupted,
    errored, context-exhausted, or the model simply stopping after the
    announcement — leaves the canvas showing that node as RUNNING forever. Cards
    are persisted at emit time, so it survives reload too: the user waits on a
    step no process is working on.

    Statuses are re-derived through ``build_workflow_event`` rather than patched
    in place, so a swept card is shaped exactly like an agent-sent one (progress
    counter, gates, currentNode) and the frontend needs no special case.
    """
    if not isinstance(run, dict) or run.get("status") != "running":
        return None
    definition = WORKFLOWS.get(str(run.get("id") or ""))
    if definition is None:
        return None

    statuses: dict[str, str] = {}
    for node in run.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        # A node that was mid-flight when the turn died IS failed — that is the
        # honest terminal state, and the only one the UI already renders.
        statuses[str(node["id"])] = "failed" if node.get("status") == "running" else str(
            node.get("status") or "pending"
        )

    event = build_workflow_event(definition, statuses, note=STALLED_NOTE)
    # A run can be left `running` with every node still `pending` (launched, then
    # the turn died before the first step reported). Nothing is failed, so the
    # derivation above still says "running" — but the run is over either way, and
    # leaving it `running` is the exact bug being fixed. Failing the run without
    # inventing a failed step keeps both halves truthful.
    if event["workflow"]["status"] == "running":
        event["workflow"]["status"] = "failed"
        event["workflow"].pop("currentNode", None)
    return event


def build_workflow_prompt(workflow: dict, extra: str = "") -> str:
    """The turn prompt injected when the user launches a workflow command.

    Composed from the workflow's own graph: preamble (input contract), the
    tool-reporting contract (node ids generated from the definition), then the
    numbered steps — each node's ``instructions``, with every gate's
    ``instructions`` inlined right after its anchor node.
    """
    wf_id = workflow["id"]
    node_ids = [n["id"] for n in workflow["nodes"]]
    nodes_json = ", ".join('{"id": "%s", "status": …}' % nid for nid in node_ids)
    extra_block = f"\nAdditional instructions from the user: {extra}\n" if extra else ""

    steps: list[str] = []
    n = 0
    for spec in workflow["nodes"]:
        n += 1
        steps.append(f"{n}. **{spec['id']}** — {spec['instructions']}")
        for gate in workflow["gates"]:
            if gate["afterNodeId"] == spec["id"] and gate.get("instructions"):
                n += 1
                steps.append(f"{n}. **gate** — {gate['instructions']}")
    steps_block = "\n".join(steps)

    return f"""You are running the named workflow **{wf_id}** — {workflow["label"]}.
{extra_block}
{workflow["preamble"]}

## Step reporting contract (mandatory)
Report EVERY step transition by calling `mcp__workflow__update_workflow` with:
- `workflow`: "{wf_id}"
- `nodes`: the FULL list, one entry per step — [{nodes_json}] — each
  status one of pending | running | done | failed
- `note`: one short sentence describing what is happening

Call it: (1) right now, with the first step running; (2) whenever a step
finishes (mark it done, the next one running); (3) when a gate sends you back
(the re-run target running, later steps pending again); (4) at the very end.
The victory-lap and report steps ALWAYS run, pass or fail — when an earlier
step failed, keep it marked failed but still complete them (victory_lap=done,
report=done) so every run ends with the double-check + wrap-up. Only a run
with no input at all to verify may stop without them.

GATE ACCOUNTING: on EVERY call whose statuses show a gate's validator step
done (from validation completion through the final all-done call), also
pass `pass_rate_pct` (the scored pass rate, 0-100) and `reruns_used`
(completed re-run loops so far — starts at 0, +1 per completed loop). The
tool REFUSES to advance past a failed gate while re-run loops remain in
budget; "budget exhausted" is true ONLY at the loop maximum, never because
of effort already spent. When the tool returns GATE BLOCKED, follow its
instructions instead of proceeding.

## Steps
{steps_block}
"""
