---
name: outsystems-design-to-app
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a design source — Figma URL, screenshot/image, HTML mockup, or structured front-end code (TSX/React/HTML, the highest-fidelity input). EXPERIMENTAL — greenfield-from-design layers on top of Mentor (built for in-flow edits) and fidelity varies; treat results as draft scaffolds, NOT ship-ready apps. Authors the design into a styling-complete spec.json (real OS UI blocks, not fake CSS; tokens, data model, sample data, chart series), then drives Mentor in batches and publishes. For prose-only briefs with NO concrete design or code, use `outsystems-spec-driven-build` instead. Use when the user asks to "build this design as an OutSystems app", "implement this Figma in OutSystems", "design to model", "design to app", "generate a screen from this mockup", "build this screen", or provides a Figma URL / image path / HTML or TSX file and wants it turned into a live OutSystems app.'
license: MIT
compatibility: Agent-neutral workflow for Codex and Claude Code (Claude Code is the most token-efficient path; see Harness notes). Requires Python 3.7+ (stdlib only) and the `outsystems` MCP server connected and authenticated, with the session-based Mentor tools available. Mentor must be enabled on the tenant. For Figma sources, the Figma MCP server must also be connected.
allowed-tools: AskUserQuestion Bash Read Write Edit mcp__outsystems__auth_status mcp__outsystems__app_list mcp__outsystems__app_create mcp__outsystems__env_list mcp__outsystems__env_app mcp__outsystems__context_screens mcp__outsystems__context_entities mcp__outsystems__context_actions mcp__outsystems__context_themes mcp__outsystems__mentor_start_session mcp__outsystems__mentor_create_asset mcp__outsystems__mentor_load_asset mcp__outsystems__mentor_prompt mcp__outsystems__mentor_get_run mcp__outsystems__mentor_cancel_prompt mcp__outsystems__mentor_publish mcp__outsystems__publish_status mcp__outsystems__publish_logs mcp__plugin_figma_figma__get_screenshot mcp__plugin_figma_figma__get_variable_defs mcp__plugin_figma_figma__get_design_context
metadata:
  version: "1.4.1"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Design-to-App

Turn a design source (Figma, screenshot, HTML mockup, or written brief) into a working OutSystems app via the OutSystems MCP / Mentor. The skill bridges three things a vanilla LLM does poorly on its own: **design extraction**, **OutSystems UI domain knowledge**, and **Mentor invocation discipline**. It authors an anatomy-first spec (a per-screen widget-tree of real blocks with inline styles), gates every visual element through a real OutSystems UI block, and drives Mentor in tight batches.

## Prerequisites

Standard catalog prereqs (see CONVENTIONS §4b), **plus** the following:
- **Mentor enabled on the tenant** (this skill drives Mentor).
- **Figma MCP server connected** if the design source is a Figma URL (`mcp__plugin_figma_figma__*` tools). For HTML / image / text sources, the Figma MCP is not required.
- A target app shell in the OutSystems environment. The skill mints one via `app_create` if the user has none — template-backed by default since ODC MCP 0.14.0, so it arrives with a theme, `Layouts` and `Common` rather than empty. **Do not** use `Template_*` / `template_*` / `OutSystems Sample Data` as the shell — Mentor's Model API rejects System modules; naming a custom template as `app_create`'s `template` argument is a different thing and is fine.

## When NOT to use

- **Just running Mentor with a free-form prompt** (no design source, no spec discipline needed): drive Mentor directly.
- **Building from a structured written spec** (no design source): use `outsystems-spec-driven-build`; it specializes in spec validation + interview + template flow.
- **Adding features to an existing app**: use `outsystems-mentor-copilot`'s `add-feature` task; it preserves more session context.
- **Auditing / reviewing an existing app**: use `outsystems-mentor-copilot`'s `quality-review` / `security-review` / `accessibility-review` tasks.

## Keep large data off the model's tokens

Three big payloads in this pipeline can each exceed 50 KB:
1. **Figma `get_design_context` XML** for complex screens
2. **The composed `spec.json`** (15–80 KB)
3. **Mentor's terminal `mentor_get_run` event** (50–500 KB of Mentor OML introspection)

For each, follow the harness disk auto-save pattern. On Claude Code the harness auto-saves oversized MCP results to disk and injects only the path; a harness without that auto-save (Codex) gets the payload inline, so write it out yourself:
- If the tool result is inline and large, save it to `$CACHE/<name>.json` and re-read only specific paths.
- If the harness auto-spills to disk (saved-to-file notice), `cp` to `$CACHE/` and **don't read the spilled file into context.**
- Pass paths, not contents, to the next pipeline step.

```
APP_NAME=<human name>
CACHE=~/.claude/cache/outsystems-design-to-app/<APP_NAME>/
SKILL=<this skill's directory>
mkdir -p "$CACHE"
```

## Procedure

The full pipeline lives in `references/workflow.md`. The MCP Mentor flow (cursor poll, session handling) lives in `references/mcp-flow.md`. The summary below is what you need to keep in context.

### Step 1: Identify the design source + the target app

Ask the user and wait for an explicit answer:
1. **Design source** (required unless pre-built spec provided): Figma URL, web URL, image path, HTML file, **structured front-end code (TSX/React/HTML)**, or written brief. A code source is the **highest-fidelity input**: it already states the tree, tokens, data model, and sample data (see `references/design-capture.md`, recipe B).
2. **App name** (required): target app in the OutSystems environment
3. **App context** (optional): path to a `context.md` describing the existing app state. The spec should reference existing entities/themes/blocks by name, not recreate them.
4. **Pre-built spec** (optional): skip to Step 4 if the user has already composed `spec.json`

App discovery:
- `mcp__outsystems__app_list { search: "<app-name>" }` → if found, capture `app_key`
- If not found → `mcp__outsystems__app_create { name: "<app-name>" }` to mint a shell — template-backed by default since ODC MCP 0.14.0; confirm via the returned `clonedFromTemplateKey`

### Step 2: Load the OutSystems UI knowledge + start design extraction (in parallel)

Load skills AND start extraction in **the same message**; they're independent and the parallelism shaves real wall-clock. See `references/workflow.md` for the exact tool-call manifest. Default load set:

```
references/design-capture.md                    # Design Capture: author ANY source directly into styling-complete spec.json sections (Step 3.0). Load FIRST
references/outsystems-ui/ui-reference.md        # OS UI widget reference: semantic hierarchy, anti-patterns, polish gates, Entities enums, Quick lookup
references/outsystems-ui/layouts.md        # LayoutSideMenu / LayoutTopMenu / LayoutBlank (delete-default gate)
references/outsystems-ui/styles-and-utilities.md  # utility classes + theme CSS variable overrides
references/outsystems-ui/patterns/{adaptive,navigation,content,numbers}.md
```

Load on demand (only when the design contains the matching element):

- **Charts**: `references/outsystems-ui/charts.md`
- **Maps**: `references/outsystems-ui/maps.md`
- **Carousel / Sidebar / DatePicker / Dropdown**: `references/outsystems-ui/patterns/interaction.md`
- **AlignCenter / Separator / gestures**: `references/outsystems-ui/patterns/utilities.md`
- **Screen archetype**: `references/screen-guides/{dashboard,list-table,detail-view,edit-form,master-detail,gallery-grid,kanban,timeline,calendar,wizard,map-view,inbox-notifications,settings}.md`
- **Cross-cutting implementation guides** (theme tokens + brand recolor, picking the right block, empty/loading/error states, reusable blocks, Reactive Web vs Phone App differences): `references/screen-guides/{design-system,component-selection,states-and-feedback,reusable-blocks,app-type-styling}.md`
- **Design tokens**: `references/outsystems-ui/design-tokens.md`
- **Field-tested gotchas** (engine-level traps and anti-patterns that bite regardless of build approach: SVG icon baking, theme class collisions, SPA visibility toggles, TableRecords seeding, etc.): `references/gotchas/INDEX.md` and the individual gotcha files. See the INDEX for the full catalog; load each on demand when the source contains the matching pattern. Sourced with attribution from `OutSystems/claude-oml-tool`'s `validated/` corpus

### Step 3: Compose `spec.json`

Sub-steps run in order (3.0 through 3d). **Do not skip ahead**; each produces output the next depends on. Step 3.0 (Design Capture) is what makes the rest rich instead of thin.

#### Step 3.0: Design Capture: author a widget-tree ANATOMY per screen (MANDATORY, FIRST)

The core artifact is a per-screen **`anatomy`** authored inside `spec.json`: a nested widget tree of **real OutSystems UI blocks with the visual styles inline** (layout, sizing, colors, backgrounds, typography), plus data bindings and chart series. It captures the screen **as-is**. Follow `references/design-capture.md`.

**Consult the OS UI blocks FIRST.** Before composing, read the block references so you build from *real* blocks with their *real* inputs/placeholders/classes, never invented ones: the skill's `references/outsystems-ui/*` (`ui-reference.md`, `styles-and-utilities.md`, patterns) and, when available, the richer **OutSystemsUI-Blocks** catalog (per-block XML anatomy + inputs + CSS) and **OutSystemsUI-Theme** (real tokens + utility classes). For each region of the design, find the matching block and read what it emits, then nest those blocks into the screen anatomy.

**Why an anatomy, not prose.** Mentor only sees the spec text. A prose description ("a stack of three compact cards…") leaves Mentor to improvise the structure and it drifts (field-tested: it built 5 giant cards, duplicated labels, empty deltas). An explicit widget tree pins nesting, which placeholder each child sits in, and the exact classes per node, so there is little to reinterpret.

The `anatomy` MUST capture every visual aspect: real blocks correctly nested; layout/sizing/colors/backgrounds/typography as **real classes** on each node (custom classes defined once in `design_system.theme_extensions`, the app.css); `bind`/`source` on every data node (render the VALUE, never a literal path); an explicit `series` on every chart; and a **KPI-source decision** (bind headline numbers to a stored metric or seed enough rows, never a live count over a tiny seed). See `references/design-capture.md` for the format, a worked Overview anatomy, and the two recipes.

#### Step 3.1: Layout + structural skeleton gates (MANDATORY: the anatomy's root layout + skeleton)

Two pre-conditions to enforce in the spec before the block-mapping pass:

- **Pick the right Layout block** (`LayoutSideMenu`, `LayoutTopMenu`, or `LayoutBlank`) based on the screen's navigation pattern. **Do not default to `LayoutBlank`** (see `layouts.md`).
- **Delete the default `LayoutTopMenu`** that `CreateScreen` ships with before adding your chosen Layout. Skipping this is the #1 cause of "two layouts at the screen root" regressions; see the inspect-delete-add code pattern in `layouts.md`.
- **Sketch the structural skeleton**: answer two questions for each Layout placeholder: *what is the column grid?* and *what are the card surfaces?* The output is a tree of `Columns*` and `Card` family blocks with NO `Container` nodes. Then commit a **block inventory** ("this region uses that block") for every visual region.

Without these gates, design pressure pushes the agent into "Container + custom CSS class" mode regardless of how good the block mapping is.

#### Step 3a: Block mapping pass (MANDATORY)

As you compose the anatomy, this pass is **validation, not invention**: collect every node's block from the `anatomy` into a **block mapping table** and confirm each resolves to a real OutSystems UI block (not custom CSS). This is an internal check; you don't need to surface the table to the user. Any node whose block is missing, vague, or a forbidden CSS-flex/grid layout is a defect, so fix the anatomy first, then re-check.

```
BLOCK MAPPING:
  KPI 5-column grid         -> Columns5 (patterns/adaptive.md)
  Customer card grid        -> Gallery RowItemsDesktop=3 (patterns/adaptive.md)
  Pipeline 5-stage strip    -> Columns5 (patterns/adaptive.md)
  Balance progress bar      -> ProgressBar (patterns/numbers.md)
  Digital adoption ring     -> ProgressCircle (patterns/numbers.md)
  Bottom 2-column row       -> Columns2 (patterns/adaptive.md)
  Customer card surface     -> custom CSS (card sub-layout, no OS block equivalent)
  Segment filter pills      -> custom CSS (no OS "pill bar" block; styled ILinks)
  Risk chip                 -> custom CSS (inline badge variant)
```

**Reject rules.** If any of these appear as "custom CSS", the mapping is wrong:

❌ **NEVER spec custom CSS flex/grid for screen-level or section-level layout.** Any region with 2+ children visually laid side-by-side or in a grid MUST use a real OS UI Adaptive block (`Columns2`–`Columns6`, `ColumnsMediumLeft`, `ColumnsMediumRight`, `ColumnsSmallLeft`, `ColumnsSmallRight`, `Gallery`, `MasterDetail`, `DisplayOnDevice`). **If an anatomy node would carry `display-flex`, `display-grid`, `flex:`, `flex-1`, `flex-direction-row`, `grid-template-columns`, or `repeat(N, 1fr)` as its section-level layout `class=`, STOP and re-spec as one of the Adaptive blocks.** See `references/outsystems-ui/patterns/adaptive.md`.

> **Two sanctioned exceptions** (everything else must be an Adaptive block):
> 1. **Inline alignment INSIDE a single block placeholder**, e.g. icon + text inside `CardItem.Left`, or "title left, action right" inside a single `Card.Content`. Never for screen-level layout where the children are independent visual blocks.
> 2. **An exact-ratio split an Adaptive block can't hit** (e.g. a 62/38 hero), allowed ONLY as a **named custom class defined once in `theme_extensions`** (e.g. `.console-hero{display:grid;grid-template-columns:62% 38%}`), never as inline CSS on the node. Prefer `ColumnsMediumLeft`/`ColumnsMediumRight`/`Columns2` when the ratio is close enough; reach for the named grid class only when the exact ratio matters.

Plus the rest:

- N equal columns (2–6): always `ColumnsN` block
- Repeating card/item grid: always `Gallery` block
- Horizontal track + fill bar: always `ProgressBar` block
- Circular/radial progress: always `ProgressCircle` block
- Tab header + content switching: always `Tabs` block
- Card-shaped surface: `Card` / `CardItem` / `CardSectioned` block
- Inline chip / numeric pill: `Tag` / `Badge` block

**Source-name to block (non-negotiable):** if a Figma frame / layer is named `Carousel` / `Carrousel` / `Slider`, use the `Carousel` block. **Do NOT** substitute `Columns3` because the screenshot shows all 3 cards side-by-side. Same for `Gallery`, `Tabs`, `Wizard`, `Accordion`, `Sidebar`, `Stepper`. Look up the block's args / placeholders in `outsystems-ui/ui-reference.md` (Quick lookup) and the matching `outsystems-ui/patterns/*.md` before writing the spec section.

#### Step 3b: Author behavior + the rest of the spec (the anatomy already carries structure/style/data)

The `anatomy` is the structural and visual source of truth; it already encodes what a 4-part prose description used to spell out, so you do NOT write separate section prose:

- **VISUAL LAYOUT**: the nested tree + inline real classes on each node.
- **DATA FLOW**: `bind=`/`source=` on each data node (name the entity/attribute; render the VALUE, never a literal path). Do NOT prescribe aggregate / action / local-variable names.
- **FUNCTIONAL BEHAVIOR**: inline annotations on interactive nodes (`onClick=…`, `onChange=…`, navigate targets). Static nodes need none.
- **PRESENTATION ORDER**: the order of nodes in the tree.

What remains to author *around* the anatomy:
- `design_system`: the complete token set plus **`theme_extensions`** (the app.css: every custom class the anatomy references, defined once; `:root` variable overrides).
- `entities`, `sample_data` (the design's real values are the seed set), `roles`, `app_chrome`, `icon_mapping`.
- `acceptance_checklist`, including the composition-fidelity gates (Step 3d).

Rules that still bind:
- Every node's block is a **real OS UI block** (Step 3a); every custom class the anatomy uses is declared in `theme_extensions` (never Tailwind class names; translate hex/px read from Tailwind into OS UI classes/vars in the anatomy).
- Every hex/px/weight comes from the **extracted design** (no generalizing: `#EDF0ED` stays `#EDF0ED`, not `#FFFFFF`).
- When app context exists, reference existing entities/classes/blocks **by name**, don't recreate.

#### Step 3c: Verify the anatomy (reject if contradicted)

Before saving `spec.json`, verify the `anatomy`:
- **Every visible region of the design is a node** (plus `app_chrome` for shared chrome); nothing dropped.
- **Every data node has a `bind`/`source`** (a value, never a literal path); **every chart node has an explicit `series`**.
- **No CSS-layout leak:** no node uses `display-flex` / `display-grid` / `grid-template-columns` / `repeat(N,` / `flex:` as **section-level layout**. Any region with 2+ children side-by-side or in a grid MUST be an Adaptive block (`Columns2`–`Columns6` / `ColumnsMediumLeft` / `ColumnsMediumRight` / `ColumnsSmallLeft` / `ColumnsSmallRight` / `Gallery` / `MasterDetail` / `DisplayOnDevice`). (The one exception: inline alignment INSIDE a single placeholder, such as icon+text or title-left+action-right.)
- **Source-name to block:** a frame named `Carousel` / `Gallery` / `Tabs` / `Wizard` / `Accordion` / `Sidebar` / `Stepper` maps to that block, not a `Columns` substitute.
- **Real block names** (from the KB) at every node; no prose where a block name belongs.
- **Custom classes resolve:** every class the anatomy references is either a stock OS utility or defined in `design_system.theme_extensions`.
- Colors/sizes/radius match the extraction, not generalized.

Save to `$CACHE/spec.json`.

#### Step 3d: Composition-fidelity + polish acceptance items (MANDATORY in the spec)

A "valid" spec with no polish reads as a wireframe; a spec that Mentor mis-executes reads as broken. Bake these gates into the spec's `acceptance_checklist` so Mentor self-verifies them during the build, not just at review time.

**Composition-fidelity gates (field-tested; each catches a real render defect):**
- **Bound expressions, not literal paths.** Every data cell/label renders the *value*; NO raw binding path (e.g. `GetX.List.Current.Entity.Attr`) may appear as visible text. (Mentor sometimes writes the path as a literal Expression value; this gate catches it.)
- **No duplicate data.** After deploy, each seeded entity has exactly the intended row count (e.g. Category=4, Record=8); the seed is idempotent (insert-only-if-empty) so a re-publish doesn't double rows.
- **KPI values match the design.** Headline numbers equal the design (e.g. 135/92/45), NOT a live count over the seed. (Per the KPI-source decision: bound to a stored metric or seeded-to-match.)
- **Charts have real data.** Every chart plots its explicit `series` (no flat/degenerate line); the segmented bar is a stacked-100% BarChart that renders as one continuous strip.
- **Charts bind to a POPULATED source, never an empty list** (field-tested; this blanked every chart on a build). Each chart's `DataPointList` / source MUST resolve to a populated aggregate over a seeded entity (or a parsed metric field). Mentor sometimes declares an empty `EmptyDataPointList` local variable and binds every chart to it, so Highcharts gets `[]` and draws nothing. The acceptance gate must verify each chart's source is a real aggregate/populated list, not a declared-but-unfilled variable.
- **Per-region styling present.** Every region has its spacing, alignment, size, typography, surface, and background/foreground applied via real OS utility classes; no run-together labels, no unstyled/flat sections, no color-unspecified regions.
- **Sizing completeness (field-tested; "structure right, look wrong" comes from here):**
  - **No dangling class.** Every custom `class=` the anatomy references is DEFINED in `theme_extensions`. An undefined class (e.g. a sparkline width) is a silent no-op, so the element grows unconstrained and squeezes siblings (this is what wrapped a `92` onto two lines).
  - **Page background APPLIED, not just defined.** The screen root / MainContent actually uses `background: var(--page-bg)` (light canvas). A defined-but-unused `--page-bg` leaves the page DARK.
  - **Charts render at a real height.** Every chart is ≥28px (sparklines ~40px, segmented bar ~14–20px) WITH zeroed Highcharts spacing; no collapsed/missing chart (a 12px bar draws nothing).
  - **Metrics don't wrap.** Numbers/labels have `white-space:nowrap` + `min-width`; grids use explicit column sizes (not three `auto`s); sparklines have a fixed defined width.

**Polish gates:**
- Default children stripped from each block (Tabs / Carousel / Accordion / etc. ship with placeholder children)
- Typography hierarchy applied (`h1` screen title, `h2` section headings, `h3` card titles, `strong` inline emphasis)
- Brand color used deliberately (2–3 uses per screen, on the most important affordances)
- Section spacing via OS UI utility classes (`margin-top-xl`, `margin-bottom-l`), NOT custom CSS
- Realistic placeholder content (real names, masked PANs, exact currency counts, not "User 1" / "Product 1" / "TBD")
- A clear focal point; section headings as `AdvancedHtml Tag="h2"`, never plain `Text` or a styled `Container`
- Final "VERIFICATION GATE" acceptance item instructing Mentor to read the app state (screens, blocks, theme CSS, entity row counts) and verify every preceding item (**including the composition-fidelity gates above**) before declaring done.

### Step 4: Confirm with the user before firing Mentor

A greenfield Mentor build is costly and slow (many minutes of Mentor runs plus tokens) and not cheaply reversible. Always show the user the spec summary (entity / screen counts, sizes) and ask for an explicit go/no-go, waiting for the answer before continuing.

> Use whatever confirmation affordance your harness provides: Claude Code has a dedicated question tool, Codex asks inline. The gate is the confirmation itself, not any particular tool.

### Step 5: Drive Mentor in batches (MCP)

See `references/mcp-flow.md` for the full cursor poll loop, session-token handling, and error categories.

**Batch strategy:**
1. **Entities + roles + seed** in the first batch. **Seeding must actually run at deploy AND be robust** (field-tested; this is the #1 time-sink and failure point):
   - Wire seeding to a **Timer scheduled When-Published** (a standalone seed action never runs on its own). Static entities seed automatically.
   - **Seed via the platform-generated `Create<Entity>` actions** (the dialect-safe path). Each seed action: (a) a Count/aggregate on the target entity, (b) an **If** that exits when it already has rows (idempotency: insert only if empty), (c) if empty, one `Create<Entity>` call per row.
   - Keep each seed **short and terminating**: a Count-guard + linear `Create` calls per row is fine; avoid deep node-per-record chains with extra branching that are pathological for Mentor's Model-API connector wiring.
   - **Verify seeding actually ran** post-publish via `app_logs` (search "Seed"): confirm each seed timer logged "finished successfully" (not an error). Empty tables mean blank tables and blank charts even when the build "succeeds".
2. **Publish this first batch before the screen batch** (see Step 6) so the data-model and seed are committed durably. A screen-turn hang can otherwise wedge the session and strand all committed-but-unpublished work, since Context Service only sees published state.
3. **Screens + theme CSS** in the next batch (resume the same open session — send it as another prompt; no token to carry).

> **Never `mentor_cancel_prompt` a turn whose work you want to keep.** A cancelled/non-terminal run discards ALL of that turn's uncommitted edits (Mentor commits only at terminal-success). If a turn hangs, start a **fresh session and re-load the same `app_key`** (which reads the last *published* OML) rather than cancelling, which is exactly why step 2 publishes the data model first.

**Spec preamble** (prepend verbatim to every batch prompt):
```
Implement the following spec COMPLETELY. Do NOT stop until every item in the
acceptance_checklist is satisfied. After all code executions, verify each
acceptance_checklist item by reading the app state; if any item fails, fix it
before finishing. Here is the spec:
```

### Step 6: Publish

After all batches succeed, publish the session (ships to the connected dev
environment — no env selection):
```
mcp__outsystems__mentor_publish { sessionId }  # returns publicationKey
# Poll publish_status { publish_key: <publicationKey> } (~15 s cadence) until outcome is success (status Finished), or failed
#   the mentor-publish path reports outcome/status, not the gateway `state` field
mcp__outsystems__env_list {}               # find the dev env_key
mcp__outsystems__env_app { env_key, key }  # key = application key (`application_key` is rejected as unknown); render `url` as a markdown link
```

**Publish is mandatory**; the session auto-GCs after 30 minutes idle.
Promoting beyond dev (Test / Prod) is a separate `deploy_start` step —
gate it with `outsystems-deploy-preview`.

Two publish outcomes are *not* a publish to retry (upstream 0.16.0, verified
2026-08-26 — details in `references/mcp-flow.md`):

- **`mentor_publish` refuses the session** → the refusal names the reason and
  the fix; the remedy is a further Mentor turn that completes the work, never a
  second `mentor_publish`. A `succeeded` run carrying `turn_error` is the usual
  cause — it is not a finished task, so the publish has nothing to take.
- **No observed outcome** (a `publish_status` response carrying
  `indeterminate: true`, the schema's Gateway-path flag) → the publish may
  still be building. Re-poll `publish_status` with the `publicationKey`, or
  verify with `env_app` — **never re-publish**; a second publish while the
  first runs is what wedges the app.

### Step 7: Report to the user (3–5 lines)

- Run ID + cache path
- App name + `app_key`
- Entity / screen counts (from the spec)
- Mentor turn count + build duration (from `duration_ms` / publish timestamps)
- Runtime URL (markdown link)
- *"Resume the same Mentor session for refinements. Or chain into `outsystems-mentor-copilot` for follow-up audits."*

## Data shape contract

The `spec.json` schema lives in `assets/enriched-blueprint.json`. Top-level keys:

- `name`, `description`, `primary_color`
- `app_chrome`: sidebar nav groups + header content, defined once, shared across all authenticated screens. Login / LayoutBlank screens set `layout_override` and skip `app_chrome`.
- `blocks`: reusable Web Blocks for patterns used on **multiple screens**. Single-screen components live inline in the screen's `anatomy`, not here.
- `design_system`: the **complete token set** (colors AND spacing/radius/shadow scales AND typography roles), plus visual_rules, css_architecture, and `theme_extensions` (the single source of truth for custom CSS / the app.css the anatomy references).
- `entities`: only if NEW entities are needed (skip when App context provided).
- `sample_data`: the seed set (design's real values, one array per entity) plus the KPI-source store (e.g. a `DashboardMetric` single-row entity). Wired to a short, idempotent, When-Published seed that uses the generated `Create<Entity>` actions (see Step 5). See the schema comment.
- `screens[]`: each with `title`, `subtitle`, an **`anatomy`** (the per-screen widget-tree, the single structural + visual source of truth, Step 3.0), optional `popups[]`, `permissions`.
- `icon_mapping`, `roles`, `acceptance_checklist` (includes the composition-fidelity gates; see Step 3d).

The **`anatomy`** is the per-screen structure (there is no separate `main_content[]`): a nested tree of real OS UI blocks with inline real classes (layout/color/bg/typography), `bind`/`source` on data nodes, `series` on chart nodes, and inline behavior annotations (`onClick`/`onChange`). See `references/design-capture.md` for the format and a worked example.

## Cache rules

- Location: `~/.claude/cache/outsystems-design-to-app/<APP_NAME>/`
- TTL: **none**. Design-to-app builds are user-initiated; the user owns retention.
- Contents: `spec.json` (the single authored artifact, styling-complete sections), `extraction.md` (Figma / HTML / image / code notes), `mentor-batch-<N>.json` (terminal responses), `publish-log.json`, `timing.log`.
- Re-running with the same spec: skip Step 3, go straight to Step 5.

> The cache path stays at `~/.claude/cache/outsystems-design-to-app/<APP_NAME>/` on **every** harness; it is a shared cross-agent cache, not a Claude-only location. The `~/.claude/` prefix is a stable path, not a Claude Code dependency.

## Troubleshooting

### Mentor errors
| Category | Action |
|---|---|
| `AuthError` | Call `mcp__outsystems__auth_status`; if expired, surface re-auth; retry ONCE |
| `tenant_not_allowed` | An allowlist gate, NOT a lapsed sign-in — re-auth and re-registering fail identically. Confirm the configured host is the tenant meant; if it is, stop and say the tenant needs enabling |
| `ValidationError` | Fix prompt/spec, retry |
| `UpstreamError` | Transient; wait and retry once |
| `InternalError` | Report to user, don't retry |

### Common spec issues
| Symptom | Cause | Fix |
|---|---|---|
| Agent builds static shell with hardcoded text | anatomy data nodes lack `bind`/`source` | Add `bind=`/`source=` to every data node in the anatomy |
| Agent skips data bindings | data node has no `bind`/`source` | Name the entity/attribute on the node; mark truly static nodes as display-only |
| Gallery shows one column | CSS grid + List widget | Use `Gallery` block instead |
| ProgressBar / Counter rendered as raw div | anatomy node written as a `<Container>` instead of the block | Use the real block name as the node (`<ProgressBar …/>`), never a styled container |
| Agent prescribes aggregate names | anatomy uses implementation terms | Name entity/attribute only; do NOT prescribe aggregate / action / variable names |
| Cards Carousel rendered as Columns3 | Source-name to block check skipped | Re-spec the region as `Carousel` block |
| Charts render blank | bound to an empty/unpopulated DataPoint list | Bind each chart to a populated aggregate over a seeded entity (see Step 3d chart gate) |
| Table / charts empty after a "successful" build | seed didn't run / errored at deploy | Seed via generated `Create<Entity>` actions (Step 5); verify the seed timer ran via `app_logs` |
| Chrome (search / theme toggle / notification badge) missing after publish | Chrome edits only implied in the screen batch | Call out `Common/ApplicationTitle` + `Common/UserInfo` explicitly in the screen-batch preamble; chrome gets skipped when not named |

### Figma extraction
- Root `get_design_context` returns metadata XML for complex screens: parse child node IDs and batch `get_design_context` on children in **pairs of 2** (4+ concurrent calls cause timeouts).
- If `get_variable_defs` returns empty, extract colors from the design-context code.
- Skip decorative nodes (vectors, masks, lines < 50px). Filter to frames > 100×50.

## Harness notes

- **Claude Code** auto-saves any MCP result larger than ~25 KB to disk and injects only the file path into context. All three big payloads in this pipeline (Figma `get_design_context` XML, the composed `spec.json`, and Mentor's 50–500 KB terminal event) routinely cross that threshold, so on Claude Code they stay out of the model's context.
- **Codex** has no such auto-save: the full MCP result is injected inline. A greenfield design-to-app build therefore costs materially more on Codex's first pass, because every large Figma extract and `mentor_get_run` payload lands in context instead of spilling to disk.
- On a harness without auto-save, write each large result to `$CACHE/` yourself and re-read only the paths you need, instead of relying on the harness spill.
- Composing `spec.json` (Step 3, the block-mapping and inline-verification passes) makes zero MCP calls: it reads the extracted design locally, so that stage costs the same on both harnesses. The divergence is entirely in the MCP-payload steps (Figma extraction, Mentor polling).

## Anti-patterns: do NOT do these

Shared rules apply (CONVENTIONS §8.4). Skill-specific:

- **Don't skip the block-mapping pass (Step 3a).** It's the single biggest source of fake UI when omitted.
- **Don't write Tailwind class names on anatomy nodes.** Figma extracts Tailwind; the anatomy uses OutSystems CSS variables and utility classes (translate hex/px read from Tailwind into OS UI classes/vars).
- **Don't generalize extracted hex codes** (`#EDF0ED` to `#FFFFFF`). If cards use `#EDF0ED` but the page uses `#FFFFFF`, those are DIFFERENT tokens.
- **Don't write block primitives as a styled `<Container>` in the anatomy.** A progress bar written as `<Container class="height-8">` makes the agent build a div; use the real block node (`<ProgressBar …/>`).
- **Don't fire Mentor without user confirmation (Step 4).** An expensive, slow, not-cheaply-reversible build shouldn't happen on assumption.
- **Don't skip the spec preamble.** It's a field-tested instruction that prevents Mentor from stopping mid-build or skipping acceptance items.
- **Don't auto-publish to Prod.** `mentor_publish` ships to the connected dev environment; promoting to Test / Prod is a separate `deploy_start` step gated by `outsystems-deploy-preview` — surface it, don't auto-promote.
- **Don't use a System-module template app as the shell.** `Template_*` / `template_*` / `OutSystems Sample Data` are rejected by Mentor's Model API; use `app_create` instead.
- **Don't load all reference docs at once.** Start with the default load set (Step 2), then load on demand based on what the design contains.
- **Don't skip the `references/gotchas/` checklist for visual-source builds.** Eleven specific engine-level traps (SVG icon baking, theme class collisions, SPA visibility toggles, TableRecords empty Source, duplicate primary actions, etc.) are documented in `references/gotchas/INDEX.md`. Each maps a specific source pattern to its fix. Field-tested against real app builds; ignoring them is the difference between a polished published surface and a "mostly works but icons are black and tables are empty" outcome.

## Related skills

- **`outsystems-spec-driven-build`**: when there's no design source, just a structured spec. Same Mentor invocation pattern, different upstream.
- **`outsystems-mentor-copilot`**: chain after a successful build for `test-generation`, `accessibility-review`, `add-feature`, etc.
- **`outsystems-app-architecture`**: visualize what was built (interactive HTML graph of screens / actions / entities).
- **`outsystems-app-documentation`**: generate Markdown docs for the new app.
- **`outsystems-deploy-preview`**: check the build before promoting to Test / Prod.

Workflow: design-to-app → mentor-copilot (test-generation + accessibility) → app-architecture (visualize) → deploy-preview (gate to Test) → publish.
