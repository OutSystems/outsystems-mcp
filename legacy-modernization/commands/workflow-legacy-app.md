---
description: Migrate a legacy app to OutSystems via the Mentor MCP — agent → validator → design_qa → victory_lap → report, with the ≥95% functional and design-fidelity gates. Out-of-app port of the named workflow.
argument-hint: spec paths + target app name (optional figma URL, tenant, run slug)
---

<!-- steps: agent, validator, design_qa, victory_lap, report -->
# /workflow-legacy-app

Same workflow id, **same node ids**, and same gate policy as `workflow-legacy-app` in
**`${CLAUDE_PLUGIN_ROOT}/app/lib/workflows.py`**. **That file is the source of truth: `Read` it first** and
follow each node's `instructions` and each gate's `instructions` as written — the
preamble's input contract, the item-granularity law, the checklist derivation and the
verdict accounting all live there and are not restated here. This command carries only
the delta for running **outside the app-generator chat UI**: no canvases, no in-process MCP
servers, and the six roles as real Claude Code subagents. Design on its own, with no
build, is `/generate-design-options`.

If `${CLAUDE_PLUGIN_ROOT}` doesn't resolve (Cursor doesn't set it), `Glob` for
`**/legacy-modernization/app/lib/workflows.py`: first in your cwd, then under the host's plugin
directory (`~/.cursor/plugins`, `~/.claude/plugins`), since the plugin is usually
installed outside your cwd. Read every plugin file named here under the root you find.

## Limited availability

**Limited availability: check access first.** Legacy modernization isn't generally
available yet. Before anything else, sign in to the OutSystems MCP (see the plugin
README's [Authorize before you run](../README.md#authorize-before-you-run)) and read
its tool list. If `modernize_session_start` isn't listed, tell the user, word for
word: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.

## User input

```text
$ARGUMENTS
```

Read it for: spec/analysis paths, the target `app_name` (or `app_key`), tenant hint,
`figma_url`, and a run slug for the report filenames. Pin anything missing from the
attached specs; if a required one can't be pinned, mark `agent` `failed` in the Progress
checklist, say exactly what to attach, and stop.

Also pin the **`extraction_id`**: the top-level field of the spec collection's
`manifest.json` (the folder is usually `generated-specs/<customer>/<extraction_id>/`). A
spec with none (a local CLI run, or one written by hand) still builds the same; only the
link step below is skipped.

## Preflight

0. **Frontier model recommended.** If this session is not already on the
   strongest model the harness offers, say so once and recommend switching
   before the first Mentor turn — mid-tier/fast models finish the workflow but
   cost more retries and cleanup. See the plugin README. Do not refuse to run
   on a cheaper model; just make the trade-off explicit.
1. **Discover the session's MCP servers and use those** — never register new ones.
   OutSystems Mentor missing → **stop** (nothing can be built). Figma missing with a
   `figma_url` in scope → ask for exports or mark `design_qa` skipped with the reason.
   Playwright missing → you cannot drive; checks become `NOT OBSERVABLE (tooling)`.
   When a server is missing, don't just stop silently — hand the user its install
   line. For OutSystems MCP, point at the plugin README section
   **If OutSystems MCP is not installed** (and
   https://github.com/OutSystems/outsystems-mcp). For the others: Figma is
   `https://mcp.figma.com/mcp`, and a Playwright MCP is
   `npx @playwright/mcp@latest` (needs Node; first run downloads browsers).
2. Authenticate on the user's OutSystems MCP before the first mentor call; on
   `AuthError`, re-auth once and retry.
3. Decide where run artifacts go — the user's project or a path they name. There is no
   Files tab: **print absolute paths**.

## Substitution table (in-app name → here)

| In-app tool | Here |
|---|---|
| `mcp__plan__update_plan` / `get_plan` | **`TodoWrite`** — one todo per individually-identified item (requirement, rule, story, screen, entity, check), published *before* the work starts |
| `mcp__workflow__update_workflow` | the **Progress checklist** below, repeated in your reply on every step/gate transition |
| `mcp__preview__agent_browser` / `get_screenshot` / `set_viewport` | the user's **Playwright MCP**, bare names: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_select_option`, `browser_take_screenshot`, `browser_resize`. `open <url>` is `browser_navigate`; `fill @eN <text>` is `browser_type`; `press Enter` is `browser_press_key` (`Enter`); `get url` / `get text` read a fresh `browser_snapshot`; `wait --text` is `browser_wait_for {text}`; `is visible` has no equivalent — check by re-reading a snapshot and stating the check + result |
| `mcp__preview__show_app` | no built-in canvas — **print the published URL**, and when this host has a canvas-equivalent surface (an IDE simple browser / preview panel, a browser MCP page, an artifact-publishing tool), **open the running app there too** so the user sees it without leaving the harness |
| `mcp__preview__show_file` | no built-in canvas — **print the absolute path** so the user can open it, and render the artifact on the host's canvas-equivalent when one exists (e.g. publish the report as an artifact page, or open it in the IDE preview) |
| `mcp__preview__render_pdf` | Playwright print-to-PDF, or local `mmdc`/`pandoc` via `Bash`; if neither exists, deliver the markdown and **say so** |
| `mcp__outsystems__*` | the user's own **OutSystems MCP** — discover at runtime, call **bare** names (for example `mentor_get_run`, `app_list`, `context_*`; publishing is whatever the catalog advertises) |
| `mcp__figma__*` | the user's own **Figma MCP**, bare names (`get_design_context`, `get_metadata`, `get_variable_defs`, `use_figma`) |
| `mcp__extractor__*` | not part of this run. If specs are missing, run `/extract-requirements` first: it extracts through the **`modernize_*`** tools on the user's OutSystems MCP |

Never hunt for an `mcp__preview__*` / `mcp__plan__*` / `mcp__workflow__*` /
`mcp__extractor__*` tool — they exist only inside the app. When a
*substitute* is also missing: degrade and **tell the user**, never silently skip and
never report PASS for behaviour you could not drive.

## Roles: what this plugin actually ships

`agents/` carries **six** subagents — `planner`, `designer`, `developer`,
`reviewer`, `tester`, `reporter`.

- **Delegate `planner` and `reporter` too.** If `Task(subagent_type: "planner")`
  or `"reporter"` fails to launch on your host, fall back to running that role
  **yourself on the main thread** from `app/prompts/planner.md` /
  `app/prompts/reporter.md` (`Read` them, apply the substitutions above) — and
  say which mode you used. Note `app/prompts/reporter.md` opens with "only when
  the user explicitly asks" — that's the ad-hoc-chat rule; in this workflow the
  `report` node **always** runs. The rest of that playbook applies unchanged.
- **Only `developer` writes app-run files** (`reviewer` and `tester` run with
  `Write`/`Edit` denied — that read-only-ness *is* the gate; `designer` may write
  ONLY its own design-mockup files in the code-mockup medium). So every report
  file (`progress-report-rev-<n>.md`, `design-qa-report-rev-<rev>.md`,
  `victory-lap-report-rev-<rev>.md`, the implementation report) is written by
  the role that owns it (`reporter`, or you) from the subagent's returned
  `handoff` block. Never grant the read-only gates write access to "fix" this.
- If a delegated `tester` reports it cannot reach `browser_*`, the tool was
  unavailable in that delegation context (the agent has no `tools:` allowlist —
  it inherits the session's) **or** the server is genuinely absent. Verify on
  the main thread: re-drive those checks yourself with `app/prompts/tester.md`
  applied inline; if the browser MCP truly isn't registered, record
  `NOT OBSERVABLE (tooling)` honestly and tell the user the install line. Say
  in the reports which of the two it was.
- **A subagent's completion message is a claim about its work, not evidence of
  it.** Before you act on a `handoff`, list the files it says it produced and
  confirm they exist at the paths given; for a scoring handoff (`reviewer`,
  `tester`), check a sample of its verdicts against the thing it scored. A
  handoff can read as successful while the files it names are missing or hold
  less than it claims: a populated report, an existing file and a file holding
  what was claimed are three different facts.

`<rev>` in every filename is the app's current published revision number.

## Steps — run in this order, keep these node ids

1. **`agent`** — build the app from the specs (+ design pack when Figma is in scope) via
   the Mentor flow. `Task` the real roles: `designer` → design-selection pause for the
   user (no QA before the pick) → **mandatory pre-build design gate** on the **picked**
   option (`reviewer` for spec/screen coverage and UX principles, *and* `tester` for
   visual QA, looping fixes back to `designer`) →
   **`planner` (delegate; inline fallback)** → `developer` (**one at a time, never in parallel** —
   single tenant, one mentor session), then loop `reviewer`(app) → `tester`(app). This
   step owns all fixes: smoke it yourself before marking it done.
   **Get a screen in front of the user early — the registry's `agent` node has the
   full rule; here is what it means with no canvases.** The chain above is a
   dependency order, not a queue: dispatch the **design-independent slice** (app
   create, the entities the data-model slice defines, their seed rows) to the
   `developer` while the pick and the design gate are still open, and have the
   `designer` cover only a **representative set** of screens per option so the pick
   arrives sooner — the rest of the chosen design is drawn while the build runs.
   Then **first screen first** (Skill `outsystems-app-build`, rule 6): the first
   publish is a screen that opens and navigates, and every chunk after it publishes
   too. **Print the app URL the moment that first screen is live** — not at the end
   of the step — and open it on the host's canvas-equivalent as the substitution
   table describes. Step 2 is briefed with that URL; the user should have had it in
   hand long before.
2. **`validator`** — **read-only** scoring, clean context: `Task` a fresh `tester`
   briefed with only the **spec file paths** and the **app URL**. It reads every spec
   file itself, derives the combined checklist, publishes it via `TodoWrite` before the
   first `browser_navigate`, and drives each item. You compute `pass_rate_pct` from its
   `TestReport` and record it in the checklist. Then delegate `reporter` (inline
   fallback) in INTERMEDIATE mode for the **intermediate Implementation Report**
   `<AppName>-r<revision>-intermediate-report.md`, from that `TestReport` and the
   `BuildReport`: the final report itself, same skeleton, status vocabulary, spec ids,
   page-1 KPI cards and appendix Z, titled "… (intermediate, validator loop <n>)", its
   lead opening *"Intermediate report: the validator gate's scoring of revision <rev>;
   the final report is this one, made final."* (see "Intermediate reports" in
   `app/prompts/reporter.md`). When the input has a `requirements.json`, run the
   handover-docs skill's `check_report_ids.py <requirements.json> <that report> --figure`
   with the same `--business-spec` / `--spec` arguments the reporter guide gives it, until
   it prints `OK`; its `REQS IMPLEMENTED X of N (P%)` line is the report's
   "REQs implemented" card. Without a `requirements.json` there is no figure, and the gate
   keeps your `pass_rate_pct`. Render it and surface it the way the substitution table
   says for `render_pdf` and `show_file`. Write one on every validator pass, including each
   loop.
3. **`design_qa`** — **read-only** design-artifact scoring: `Task` `reviewer` with the
   claim tables + app URL, scoring via Skill **`outsystems-ui-exactness`** (claim files are the
   source of truth; screenshots are evidence). In the code-mockup medium the chosen
   option's mockup files are the design artifact — derive the claims from them and score
   the built app against them the same way. You write `design-qa-report-rev-<rev>.md`
   from its `ReviewReport`. No design artifact in scope at all (no Figma AND no mockups)
   → `skipped` with the reason, and the design gate is skipped with it.
4. **`victory_lap`** — **always runs, pass or fail.** `Task` a fresh `tester` to re-drive
   the app screen by screen and re-check tenant state against the validator's checklist;
   you write `victory-lap-report-rev-<rev>.md` with what stands, what doesn't, and every
   discrepancy.
5. **`report`** — **always runs.** First write and run the **Test Evidence Pack**
   yourself (Skill `outsystems-test-evidence-pack`): scaffold it from the extraction's
   `requirements.json`, write one test per flow from the tester's `pack` entries (each
   keeping the entry's `test_id` as its `testId(...)` tag, unless another pack test
   already has that id: that test keeps it, and the new one takes the next free id
   `check_pack.py` prints) plus
   the signed-out `@ACCESS` checks, run `check_pack.py` and `npm test`, and hand the
   reporter its `summary.json` and matrix (its section 5 names each requirement's tests
   by those test ids). Then delegate `reporter` (inline fallback):
   `<AppName>-r<revision>-report.md` is the **last intermediate report, made final**:
   copy it, drop the intermediate title suffix and lead line, keep its ids and statuses,
   and add the victory lap's findings and the evidence links. Its
   `check_report_ids.py --figure` line may not show fewer requirements implemented than
   the intermediate report's: a status the victory lap overturns goes back through the
   `validator` gate (a loop, then a new intermediate report), never quietly into the final
   report. It keeps the shared 0–9 + A skeleton and the document
   family's look (the same as the Business Spec's): the page-1 KPI cards, the data-model
   diagrams, site map and (with two or more apps) app landscape drawn the way the spec
   draws them, the per-item requirements list in the fixed status vocabulary (tested? why
   not?), the pass-rate progression across any
   loops, gaps and next steps. Print its absolute path. Close the **chat** message (never
   the report file) with the lesson-capture offer from the substitution table, naming 1-3
   concrete candidate lessons from this run.

## Link the build to its extraction

Pass the pinned `extraction_id` in **every** `developer` brief. The developer links each
new `conversation_id` + `app_key` pair with **`modernize_generation_link`** as soon as it
has it, early in the build, so even an abandoned run is traced, and reports each pair's
outcome in its `mentor_conversations` (`link`). It lets a migration be traced end to end.

- **After each handoff** (delegated, or the inline fallback on a host without subagents),
  tally the `link` outcomes into `links`. For an entry the developer never sent (no
  `link`, or `skipped: tool missing`, since a delegation can lack a tool the main thread
  has), call the tool yourself once for that pair, bare name, same rules. Never repeat an
  `ok`, `error` or timeout: the call was made, and each one writes a line.
- **Best effort:** a missing tool (a tenant whose gateway or extractor does not serve it
  yet), an error or a timeout is noted in `links` and the run carries on. Retry once only
  on `service_unavailable`; never on a timeout or a named refusal such as `bad_id`, since
  each call writes a line.
- **Skip** when no `extraction_id` was pinned, or an entry has no `conversation_id`.

## Gates

Two gates, **separate counters**, both re-running the same step. Full text:
`_migration_gates()` in `app/lib/workflows.py`.

| Gate | After | Passes at | Re-runs | Max re-runs |
|---|---|---|---|---|
| Functional | `validator` | **≥95%** of the validator's combined checklist PASS **and** ≥95% "REQs implemented" in the intermediate report | `agent` | **5** |
| Design fidelity | `design_qa` | **≥95%** of built screens PASS `outsystems-ui-exactness` claim scoring | `agent` | **5** |

- **The functional gate's pass rate is the LOWER of** your `pass_rate_pct` and the
  intermediate report's `REQS IMPLEMENTED` percentage (when the input has a
  `requirements.json`). So a report reading 5% can never follow a passed gate.
- Score by the file's verdict accounting — `PASS` only in the numerator, a `PARTIAL` is
  **never** rounded up, `NOT OBSERVABLE` leaves the denominator.
- **Below the threshold with loops remaining you MUST loop back.** "Close enough",
  "effort already spent" and "diminishing returns" are workflow violations.
- **Before each loopback:** (a) write `progress-report-rev-<reruns_used+1>.md` with the
  scored checklist, the pass rate, what failed and the scope of the re-run, and print its
  path; (b) set `agent: running` and the scorer back to `pending` in the checklist;
  (c) re-run `agent` scoped to **only** the failing items / claim ids.
- Fixes happen **only** inside the `agent` re-run — `validator` and `design_qa` never fix,
  edit, publish or start a mentor run.
- `reruns_used` starts at 0 and increments by exactly 1 per completed loop. After the
  **5th** completed loop, proceed with the residual gaps recorded in the reports.

## Progress tracking (no canvases here)

Two surfaces, both yours to maintain:

- **`TodoWrite`** replaces the Plan canvas and carries the granularity law — one todo per
  individually-identified thing, titled with its source id (`BR-07 — Overdue loans block
  new checkouts`). A bucket todo ("Implement the business rules", "Test the app") is a
  bug. Every check a scoring step is about to drive must be listed **before** it drives.
- **The Progress checklist** replaces the Workflow canvas. Re-emit this block in your
  reply on every transition:

```markdown
## /workflow-legacy-app progress
- run: ‹slug› | app: ‹app_name / app_key› | url: ‹published URL›
- first_screen: ‹screen name @ HH:MM, or not yet› — the first publish the user could open
- figma: ‹url | none› | roles: ‹which of the six were delegated vs run inline›
- agent: pending|running|done|failed
- validator: pending|running|done|failed — pass_rate_pct=… reruns_used=…
- gate_functional: open|passed|exhausted
- design_qa: pending|running|done|failed|skipped — pass_rate_pct=… reruns_used=…
- gate_design: open|passed|exhausted|skipped
- victory_lap: pending|running|done
- report: pending|running|done
- links: ‹n recorded› | skipped: ‹no extraction_id / tool missing / error / timeout›
```

Never mark a gate `passed` without a measured `pass_rate_pct` meeting its threshold (or a
stated skip reason).

## Done when

`victory_lap` and `report` are `done`, the report path is printed, and each gate is
`passed`, `exhausted` with the residual gaps recorded, or `skipped` with the reason, and
`links` is recorded or skipped with the reason.
