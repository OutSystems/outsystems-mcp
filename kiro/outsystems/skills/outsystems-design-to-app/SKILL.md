---
name: outsystems-design-to-app
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a design source — Figma URL, screenshot/image, HTML mockup, or structured front-end code (TSX/React/HTML, the highest-fidelity input). EXPERIMENTAL — greenfield-from-design layers on top of Mentor (built for in-flow edits) and fidelity varies; treat results as draft scaffolds, NOT ship-ready apps. Authors the design into a styling-complete spec.json (real OS UI blocks, not fake CSS; tokens, data model, sample data, chart series), then drives Mentor in batches and publishes. For prose-only briefs with NO concrete design or code, use `outsystems-spec-driven-build` instead. Use when the user asks to "build this design as an OutSystems app", "implement this Figma in OutSystems", "design to model", "design to app", "generate a screen from this mockup", "build this screen", or provides a Figma URL / image path / HTML or TSX file and wants it turned into a live OutSystems app.'
license: MIT
compatibility: Agent-neutral workflow for Codex and Claude Code. Requires the `outsystems` MCP server connected and authenticated, with the session-based Mentor tools available, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant. For Figma sources, the Figma MCP server must also be connected.
metadata:
  version: "1.5.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Design-to-App

Turn a design source (Figma, screenshot, HTML mockup, or front-end code) into a working OutSystems app via the OutSystems MCP / Mentor. The skill bridges three things a vanilla LLM does poorly on its own: **design extraction**, **OutSystems UI domain knowledge**, and **Mentor invocation discipline**. It authors an anatomy-first spec (a per-screen widget-tree of real blocks with inline styles), gates every visual element through a real OutSystems UI block, and drives Mentor in tight batches.

**Session, polling and publish rules come from the main `outsystems` skill** (read `tools/list`, one Mentor session per task, cursor polling, the status watcher, confirm before every tenant write). This skill adds only what is specific to building from a design; where the two seem to differ, the main skill wins.

## Prerequisites

- **The `outsystems` MCP server connected and authenticated**, per the main `outsystems` skill.
- **Mentor enabled on the tenant** (this skill drives Mentor).
- **Figma MCP server connected** if the design source is a Figma URL (`mcp__plugin_figma_figma__*` tools). For HTML / image / code sources, the Figma MCP is not required.
- **A target app.** Either an existing app the user names, or a new one the skill creates (after confirmation) by cloning the tenant's own **"Template Web App"**; see Step 1.

## When NOT to use

- **Just running Mentor with a free-form prompt** (no design source, no spec discipline needed): drive Mentor directly with your prompt.
- **Building from a structured written spec** (no design source): use `outsystems-spec-driven-build`; it specializes in spec validation + interview + template flow.
- **Adding non-visual features to an existing app** (logic, data, integrations, no design source): drive Mentor directly with your prompt. Adding a **screen from a design** to an existing app *is* in scope: see "Adding a screen to an existing app" under Step 1.
- **Auditing / reviewing an existing app**: drive Mentor directly with your prompt.

## Keep large data off the model's tokens

Figma `get_design_context` XML, the composed `spec.json` (15–80 KB) and Mentor's terminal `mentor_get_run` events (50–500 KB) are all large. If a large result arrives inline, save it to the working folder and re-read only what you need; if the harness already saved it to disk, pass that path on and don't read the whole file into context.

**Working folder:** keep the build's files in a `design-to-app/<APP_NAME>/` folder inside the user's current workspace (create it with the file-write tool), not in the home folder. See Working folder below.

## Procedure

The full pipeline lives in `references/workflow.md`. The Mentor call sequence this skill uses (create or load the app, batches, publish) lives in `references/mcp-flow.md`; the generic session, polling and publish rules live in the main `outsystems` skill. The summary below is what you need to keep in context.

### Step 1: Identify the design source + the target app

Ask the user and wait for an explicit answer:
1. **Design source** (required unless pre-built spec provided): Figma URL, image path, HTML file, web URL (screenshot it with a browser tool, then follow the image recipe), or **structured front-end code (TSX/React/HTML)**. A code source is the **highest-fidelity input**: it already states the tree, tokens, data model, and sample data (see `references/design-capture.md`, recipe B).
2. **App name** (required): target app in the OutSystems environment
3. **App context** (optional): anything the user already knows about the existing app (a `context.md`, notes). For an existing app the skill gathers the context itself anyway (see "Adding a screen to an existing app" below), so this is a supplement, not a requirement.
4. **Pre-built spec** (optional): skip to Step 4 if the user has already composed `spec.json`

App discovery (read the live `tools/list` first; argument names below are illustrative, the tool schemas are the source of truth):
- `app_list { search: "<app-name>" }` → if found, capture its key as `app_key`. Load it into a Mentor session (`mentor_start_session` → `mentor_load_asset`) when you first need it: during Step 1 if you need Mentor for its context (below), otherwise in Step 5. Keep that one session for the whole build.
- If not found, **creating an app is a tenant write: restate it ("create a new Web app named X, cloned from your tenant's Template Web App") and wait for explicit confirmation.** Then:
  1. `app_list { search: "Template Web App", detailed: true }` → the tenant's own template. Its `assetKey` is the `templateAssetKey` and its `portfolioKey` is the portfolio for the new app. Do **not** fall back to the built-in default template: it pins outdated OutSystems UI / Charts / Maps versions, the first publish then fails at the draft-save step, and Mentor cannot repoint the pins.
  2. `mentor_start_session` → `mentor_create_asset { sessionId, assetType: "WebApplication", name, templateAssetKey, portfolioKey }`. **Pass `portfolioKey`:** the schema marks it optional, but the server rejects the call without it ("Portfolio ID is required"). Use the template's portfolio unless the user names another; never guess one. The new asset is already in this session: keep using **this same session** for every batch. Capture the returned `applicationKey` as `app_key`.
  3. The new app appears in the catalog (`app_info`, `app_refs`, `app_list`, the context lookups) **only after its first publish**. Until then, don't look it up there.
- **Fallback** when there is no "Template Web App" on the tenant, or creation fails: ask the user to create the app in ODC Studio, then find it with `app_list` and load it with `mentor_load_asset`.
- **The MCP cannot delete apps.** Before creating, check `app_list` for an app with the same name, so a retry doesn't leave duplicates behind; and reuse one `app_key` across rebuilds of the same design (see `references/gotchas/iterative-deployments.md`).

#### Adding a screen to an existing app

When the target app already exists, the design is a new screen (or a restyle) **inside** that app, not a new app. Before composing the spec:

1. **Gather the app's context yourself**, in parallel: `context_screens`, `context_entities` and `context_themes` for the app (its layout block, menu, theme and grid), plus `context_actions` when the screen needs existing logic. These see only what has been **published**. When they can't answer something (a block's internals, how the menu is built), load the app into the session now and ask Mentor a read-only question, e.g. "List the screens, the layout block and the Menu links of this app. Change nothing and do NOT publish."
2. **Fit the spec to what exists:**
   - **Entities:** reuse existing entities and attributes by name; add only what the design needs and the app lacks. Don't re-seed entities that already hold data; seed only new ones.
   - **Layout and chrome:** use the app's existing layout block and `Common` chrome. Don't rebuild `ApplicationTitle` / `UserInfo`; add the new screen as a link in the existing Menu instead. Leave out the batch prompt's SHARED CHROME paragraph unless the user asks for chrome changes.
   - **Theme:** the app's theme wins where it conflicts with the design, unless the user asks to restyle. Put only the classes the new screen needs in `theme_extensions`, prefixed with the screen name, and *add* them to the theme: never replace existing rules or `:root` values.
3. **Batches:** if there is nothing new in the data model, skip batch 1 and send only the screen batch (with its own publish confirmation). Otherwise batch 1 carries only the new entities and their seed.
4. **Acceptance checklist:** add "existing screens, entities and theme rules are unchanged" and "the new screen is reachable from the Menu".

### Step 2: Load the OutSystems UI knowledge + start design extraction (in parallel)

Load the references AND start extraction in **the same message**; they're independent and the parallelism shaves real wall-clock. See `references/workflow.md` for the exact tool-call manifest. Default load set:

```
references/design-capture.md                    # Design Capture: author ANY source directly into styling-complete spec.json sections (Step 3.0). Load FIRST
references/outsystems-ui/ui-reference.md        # OS UI widget reference: semantic hierarchy, anti-patterns, polish gates, Entities enums, Quick lookup
references/outsystems-ui/layouts.md        # LayoutSideMenu / LayoutTopMenu / LayoutBlank (exactly one Layout per screen)
references/outsystems-ui/styles-and-utilities.md  # utility classes + theme CSS variable overrides
references/outsystems-ui/patterns/{adaptive,navigation,content,numbers}.md
```

Load on demand (only when the design contains the matching element):

- **Charts**: `references/outsystems-ui/charts.md`
- **Maps**: `references/outsystems-ui/maps.md`
- **Carousel / Sidebar / DatePicker / Dropdown**: `references/outsystems-ui/patterns/interaction.md`
- **AlignCenter / Separator / gestures**: `references/outsystems-ui/patterns/utilities.md`
- **Screen archetype**: `references/screen-guides/{dashboard,list-table,detail-view,edit-form,master-detail,gallery-grid,kanban,timeline,calendar,wizard,map-view,inbox-notifications,settings}.md`
- **Cross-cutting implementation guides** (theme tokens + brand recolor, picking the right block, empty/loading/error states, reusable blocks, styling defaults when the design is silent): `references/screen-guides/{design-system,component-selection,states-and-feedback,reusable-blocks,app-type-styling}.md`
- **Field-tested gotchas** (engine-level traps and anti-patterns that bite regardless of build approach: SVG icon baking, theme class collisions, SPA visibility toggles, TableRecords seeding, etc.): `references/gotchas/INDEX.md` and the individual gotcha files. See the INDEX for the full catalog; load each on demand when the source contains the matching pattern.

### Step 3: Compose `spec.json`

Sub-steps run in order (3.0 through 3d). **Do not skip ahead**; each produces output the next depends on. Step 3.0 (Design Capture) is what makes the rest rich instead of thin.

#### Step 3.0: Design Capture: author a widget-tree ANATOMY per screen (MANDATORY, FIRST)

The core artifact is a per-screen **`anatomy`** authored inside `spec.json`: a nested widget tree of **real OutSystems UI blocks with the visual styles inline** (layout, sizing, colors, backgrounds, typography), plus data bindings and chart series. It captures the screen **as-is**. Follow `references/design-capture.md`.

**Consult the OS UI blocks FIRST.** Before composing, read the block references so you build from *real* blocks with their *real* inputs/placeholders/classes, never invented ones: the skill's `references/outsystems-ui/*` (`ui-reference.md`, `styles-and-utilities.md`, patterns). For each region of the design, find the matching block and read its inputs and placeholders, then nest those blocks into the screen anatomy.

**Why an anatomy, not prose.** Mentor only sees the spec text. A prose description ("a stack of three compact cards…") leaves Mentor to improvise the structure and it drifts (field-tested: it built 5 giant cards, duplicated labels, empty deltas). An explicit widget tree pins nesting, which placeholder each child sits in, and the exact classes per node, so there is little to reinterpret.

The `anatomy` MUST capture every visual aspect: real blocks correctly nested; layout/sizing/colors/backgrounds/typography as **real classes** on each node (custom classes defined once in `design_system.theme_extensions`, the app.css); `bind`/`source` on every data node (render the VALUE, never a literal path); an explicit `series` on every chart; and a **KPI-source decision** (bind headline numbers to a stored metric or seed enough rows, never a live count over a tiny seed). See `references/design-capture.md` for the format, a worked Overview anatomy, and the two recipes.

#### Step 3.1: Layout + structural skeleton gates (MANDATORY: the anatomy's root layout + skeleton)

Two pre-conditions to enforce in the spec before the block-mapping pass:

- **Pick the right Layout block** (`LayoutSideMenu`, `LayoutTopMenu`, or `LayoutBlank`) based on the screen's navigation pattern. **Do not default to `LayoutBlank`** (see `layouts.md`).
- **Exactly one Layout block at the screen root.** State in the spec that any default layout added when Mentor creates the screen is replaced by the chosen one, and add it as an acceptance item; two Layouts at the root is a common regression (see `layouts.md`).
- **Sketch the structural skeleton**: answer two questions for each Layout placeholder: *what is the column grid?* and *what are the card surfaces?* The output is a tree of `Columns*` and `Card` family blocks, with no `Container` standing in for a column grid or a card. (Containers are still fine for the two sanctioned exceptions in Step 3a: inline alignment inside one placeholder, and a named exact-ratio class.) Then commit a **block inventory** ("this region uses that block") for every visual region.

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
  Segment filter pills      -> custom CSS (no OS "pill bar" block; styled Links)
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

The `anatomy` is the structural and visual source of truth; don't write separate section prose. Data nodes carry `bind=`/`source=` naming the entity/attribute (render the VALUE, never a literal path; don't prescribe aggregate / action / variable names). Interactive nodes carry inline behaviour (`onClick=…`, `onChange=…`, navigate targets).

What remains to author *around* the anatomy:
- `design_system`: the complete token set plus **`theme_extensions`** (the app.css: every custom class the anatomy references, defined once; `:root` variable overrides).
- `entities`, `sample_data` (the design's real values are the seed set), `roles`, `app_chrome`, `icon_mapping`.
- `acceptance_checklist`, including the composition-fidelity gates (Step 3d).

Rules that still bind:
- Every node's block is a **real OS UI block** (Step 3a); every custom class the anatomy uses is declared in `theme_extensions` (never Tailwind class names; translate hex/px read from Tailwind into OS UI classes/vars in the anatomy).
- Write special characters literally (`▲`, `▼`, `·`, `–`, `€`). Never write `\uXXXX` escapes in an anatomy line or a sample value: Mentor copies them into Expressions verbatim, so the screen shows `\u25b2` instead of ▲.
- Every hex/px/weight comes from the **extracted design** (no generalizing: `#EDF0ED` stays `#EDF0ED`, not `#FFFFFF`).
- For an existing app, reference existing entities/classes/blocks **by name** (from the context you gathered in Step 1), don't recreate.

#### Step 3c: Verify the anatomy (reject if contradicted)

Before saving `spec.json`, verify the `anatomy`:
- **Every visible region of the design is a node** (plus `app_chrome` for shared chrome); nothing dropped.
- **Every data node has a `bind`/`source`** (a value, never a literal path); **every chart node has an explicit `series`**.
- **No CSS-layout leak:** no node uses `display-flex` / `display-grid` / `grid-template-columns` / `repeat(N,` / `flex:` as **section-level layout**. Any region with 2+ children side-by-side or in a grid MUST be an Adaptive block (`Columns2`–`Columns6` / `ColumnsMediumLeft` / `ColumnsMediumRight` / `ColumnsSmallLeft` / `ColumnsSmallRight` / `Gallery` / `MasterDetail` / `DisplayOnDevice`). (The two Step 3a exceptions: inline alignment inside one placeholder, and a named exact-ratio class defined in `theme_extensions`.)
- **Source-name to block:** a frame named `Carousel` / `Gallery` / `Tabs` / `Wizard` / `Accordion` / `Sidebar` / `Stepper` maps to that block, not a `Columns` substitute.
- **Real block names** (from `references/outsystems-ui/`) at every node; no prose where a block name belongs.
- **Custom classes resolve:** every class the anatomy references is either a stock OS utility or defined in `design_system.theme_extensions`.
- Colors/sizes/radius match the extraction, not generalized.

Save to `spec.json` in the working folder.

#### Step 3d: Composition-fidelity + polish acceptance items (MANDATORY in the spec)

A "valid" spec with no polish reads as a wireframe; a spec that Mentor mis-executes reads as broken. Bake these gates into the spec's `acceptance_checklist` so Mentor self-verifies them during the build, not just at review time.

**Composition-fidelity gates (field-tested; each catches a real render defect):**
- **Bound expressions, not literal paths.** Every data cell/label renders the *value*; NO raw binding path (e.g. `GetX.List.Current.Entity.Attr`) may appear as visible text. (Mentor sometimes writes the path as a literal Expression value; this gate catches it.)
- **No duplicate data.** After deploy, each seeded entity has exactly the intended row count (e.g. Category=4, Record=8); the seed is idempotent (insert-only-if-empty) so a re-publish doesn't double rows.
- **KPI values match the design.** Headline numbers equal the design (e.g. 135/92/45), NOT a live count over the seed. (Per the KPI-source decision: bound to a stored metric or seeded-to-match.)
- **Charts have real data.** Every chart plots its explicit `series` (no flat/degenerate line); the segmented bar is a stacked-100% BarChart that renders as one continuous strip.
- **Charts bind to a POPULATED source, never an empty list** (field-tested; this blanked every chart on a build). Each chart's `DataPointList` / source MUST resolve to a populated aggregate over a seeded entity (or a parsed metric field). Mentor sometimes declares an empty `EmptyDataPointList` local variable and binds every chart to it, so Highcharts gets `[]` and draws nothing. The acceptance gate must verify each chart's source is a real aggregate/populated list, not a declared-but-unfilled variable.
- **Values formatted as the design shows them.** Counts, amounts and dates render with the design's formatting (thousands separators, currency, decimals, date format): `1,284` not `1284`, `$1,240.00` not `1240`. Use FormatDecimal / FormatCurrency / FormatDateTime, or seed a ready-formatted text field.
- **Per-region styling present.** Every region has its spacing, alignment, size, typography, surface, and background/foreground applied via real OS utility classes; no run-together labels, no unstyled/flat sections, no color-unspecified regions.
- **Sizing completeness (field-tested; "structure right, look wrong" comes from here):**
  - **No dangling class.** Every custom `class=` the anatomy references is DEFINED in `theme_extensions`. An undefined class (e.g. a sparkline width) is a silent no-op, so the element grows unconstrained and squeezes siblings (this is what wrapped a `92` onto two lines).
  - **Page background APPLIED, not just defined.** The screen root / MainContent actually uses `background: var(--page-bg)` (light canvas). A defined-but-unused `--page-bg` leaves the page DARK.
  - **Charts render at a real height.** Every chart widget is ≥28px tall (sparklines ~40px) WITH zeroed Highcharts spacing; a thin segmented bar keeps a ≥28px widget and gets its thin look from the bar's own thickness (~14px), not from a shorter widget. No collapsed/missing chart (a 12px widget draws nothing).
  - **Metrics don't wrap.** Numbers/labels have `white-space:nowrap` + `min-width`; grids use explicit column sizes (not three `auto`s); sparklines have a fixed defined width.

**Polish gates:**
- Default children stripped from each block (Tabs / Carousel / Accordion / etc. ship with placeholder children). **Breadcrumbs** in particular ships with "Dashboard > List > Detail": replace its items with the design's trail (e.g. "Home / Orders"), or remove the block if the design has none.
- Typography hierarchy applied (`h1` screen title, `h2` section headings, `h3` card titles, `strong` inline emphasis)
- Brand color used deliberately (2–3 uses per screen, on the most important affordances)
- Section spacing via OS UI utility classes (`margin-top-xl`, `margin-bottom-l`), NOT custom CSS
- Realistic placeholder content (real names, masked PANs, exact currency counts, not "User 1" / "Product 1" / "TBD")
- A clear focal point; section headings as `AdvancedHtml Tag="h2"`, never plain `Text` or a styled `Container`
- Final "VERIFICATION GATE" acceptance item instructing Mentor to read the app state (screens, blocks, theme CSS, entity row counts) and verify every preceding item (**including the composition-fidelity gates above**) before declaring done.

### Step 4: Confirm with the user before firing Mentor

A greenfield Mentor build is costly and slow (many minutes of Mentor runs) and not cheaply reversible. Always show the user the spec summary (entity / screen counts, sizes, the two batches) and ask for an explicit go/no-go, waiting for the answer before continuing. Expect roughly 20–40 minutes of Mentor time for a rich screen, and say so.

State each screen's access in the summary: screens require login by default. Make a screen anonymous only if the user asks for a public screen, and say so here so it's a visible choice. Don't make one anonymous just to make the Step 6b screenshot easier.

This go/no-go covers the Mentor edits only. **Each tenant write still gets its own confirmation:** creating the app (Step 1) and every publish (Steps 5 and 6), as the main `outsystems` skill requires. Editing in a Mentor session changes only the session's in-memory OML, so the prompts themselves need no extra confirmation.

> Use whatever confirmation affordance your harness provides: Claude Code has a dedicated question tool, Codex asks inline. The gate is the confirmation itself, not any particular tool.

### Step 5: Drive Mentor in batches (MCP)

Use **one Mentor session for the whole build**: the session that created the app, or a new session with the existing app loaded by `mentor_load_asset`. Send each batch as a `mentor_prompt` on that session, one turn at a time, and poll each run to terminal **following the main `outsystems` skill** (cursor polling, the status watcher, wait only on statuses the live `mentor_get_run` schema lists, read the completion signals before reporting done). `references/mcp-flow.md` has the call sequence for this skill.

**Batch strategy** (2 batches, field-tested; more turns means unacceptable latency, so do NOT decompose section-by-section):
1. **Entities + roles + seed** in the first batch. **Seeding must actually run at deploy AND be robust** (field-tested; this is the #1 time-sink and failure point):
   - Wire seeding to a **Timer scheduled When-Published** (a standalone seed action never runs on its own). Static entities seed automatically.
   - **Seed via the platform-generated `Create<Entity>` actions** (the dialect-safe path). Each seed action: (a) a Count/aggregate on the target entity, (b) an **If** that exits when it already has rows (idempotency: insert only if empty), (c) if empty, one `Create<Entity>` call per row.
   - Keep each seed **short and terminating**: a Count-guard + linear `Create` calls per row is fine; avoid deep node-per-record chains with extra branching that are pathological for Mentor's Model-API connector wiring.
   - **Verify seeding actually ran** post-publish via `app_logs` (search "Seed"): confirm each seed timer logged "finished successfully" (not an error). Empty tables mean blank tables and blank charts even when the build "succeeds".
2. **Publish this first batch before the screen batch** (see Step 6; confirm with the user first). Everything a turn changes lives only in the session until it is published, so this gives the screen batch a durable base: a failure later costs one turn, not the whole build.
3. **Screens + theme CSS + charts + chrome** in the second batch, as another prompt on the same session.

> **Don't cancel a turn whose work you want to keep.** A cancelled turn's own edits don't land. Let a slow turn reach terminal; if it fails or times out, retry in the **same session** with a narrower, more concrete prompt, as the main `outsystems` skill describes. That is also why step 2 publishes the data model first.

**The batch prompt** (the single prompt block: prepend it verbatim to every batch, then append that batch's slice of `spec.json`):
```
Implement the following spec COMPLETELY, in this turn. Apply every change now:
do NOT reply with a plan, and do NOT ask whether to proceed. Do NOT publish
the app in this turn: publishing is done separately, after the user confirms.
Do NOT stop until every item in the acceptance_checklist is satisfied. After all code executions,
verify each acceptance_checklist item by reading the app state; if any item
fails, fix it before finishing.

ENGINE-LEVEL HARD RULES, for every screen in the spec:

(R1) THEME CLASS COLLISIONS. Never use these class names on any widget or in
     the theme CSS: main-content, sidebar, header, content, footer, main,
     layout. They collide with OutSystems UI's layout rules. Prefix custom
     classes with the app name (e.g. banking-sidebar). For link colours, use
     !important to beat the theme's a { color: inherit !important } rule.
(R2) ICONS. Use the OutSystems UI Icon widget with its Icon property set to the
     bare Phosphor name (e.g. "house"). Never use <i class="ph ph-X"> markup:
     it does not render in ODC. On dark or coloured surfaces give the icon an
     explicit light colour class. If an inline SVG is unavoidable, set
     fill="#fff" (and stroke) on the <svg> element itself.
(R3) SEEDED DATA THAT SURVIVES DEPLOY. Every table, list and chart is bound to
     an aggregate over a seeded entity, never to an empty or unset source. Seed
     each entity with an idempotent action (Count guard, If empty, one generated
     Create<Entity> call per row) run by a Timer scheduled When-Published.
     Do NOT seed with SQL or Advanced SQL INSERT statements: they have failed
     at runtime on ODC and left every table empty. Seed every value exactly as
     given in sample_data, dates included: a date is a literal date, never
     CurrDate() / CurrDateTime(). Never let seeding run twice.
(R4) NO WIDGETS INSIDE LINKS. Never put an Input, Upload, Button, Form, Table
     or Chart inside a Link widget; the Link intercepts the clicks. Use a Link
     only when the whole element is a navigation target (a clickable card/row).
(R5) ONE WIDGET PER ACTION. Each action on a screen is one Button or Link,
     wired once. Never add a second button for the same action.
(R6) ONE SCREEN PER SECTION. Each section of the design is its own screen;
     never hide sections with display:none toggles. Overlays (popups, toasts,
     side panels) use the real OutSystems UI widgets for them.

SHARED CHROME (include this paragraph only when app_chrome.header lists more
than the brand and the avatar): before any screen work, (1) style the existing
app-name Expression in Common/ApplicationTitle per app_chrome.header, using its
ExtendedClass, without adding a new wordmark widget; (2) add to Common/UserInfo,
left to right, the chrome icon cluster (search / theme toggle / notification
IconBadge with its count), a welcome-text Expression, then the existing
UserAvatar; (3) in the Layout's Header (LayoutTopMenu) or Navigation
(LayoutSideMenu) placeholder, place the Menu block from Common with the Link
widgets directly inside Menu.PageLinks. Read each block's widget tree back and
confirm the children landed before starting the screens.

Here is the spec:
```

This is the only prompt block. `references/workflow.md` and `references/mcp-flow.md` point here rather than restating it. The rules map to `references/gotchas/` (R1 theme-collisions, R2 svg-icon-baking, R3 tablerecords-seeding, R4 widget-link-slot, R5 duplicate-buttons, R6 spa-section-visibility).

### Step 6: Publish

Publishing is a tenant write. **Before every publish** (after batch 1 and after batch 2), restate what will be published ("publish the data model and seed of app X to its development environment") and wait for explicit confirmation. Then publish the **session** (never an app key) the way the live server accepts:

- **`mentor_publish { sessionId, comment }`** (publish note, 500 characters max), then poll `publish_status` with the returned key to terminal, as the main `outsystems` skill describes.
- **If `mentor_publish` answers that it is deprecated** ("Use mentor_prompt with the message \"Publish\" instead"; `tools/list` may still advertise it), send **`mentor_prompt { sessionId, message: "Publish" }`** on the same session instead. It is the same publish, so the confirmation you already have covers it. Poll that run to terminal like any Mentor turn; it yields a publication key, so then poll `publish_status` with that key until `outcome` is terminal (`success`, with `status: Finished`), and confirm the app's revision advanced with `app_info` or `env_app` before reporting success.

Never re-publish on a refusal or an unobserved outcome: a refusal is answered by a further Mentor turn, and an unobserved outcome is re-polled or checked with `env_app`.

When the final publish has landed:
- Fetch the runtime URL with `env_app` (the application argument is `key`), using the environment the publish reports or the development environment from `env_list`, and give the user the `url` as a link.
- Check seeding ran (`app_logs`, search "Seed"), and spot-check the screens with the context lookups. Mentor's own self-check can report success on work that didn't land, so the rendered app and the logs are the real check: **do Step 6b before reporting.**
- Release the session (`mentor_close_session`) once the work is published, if the user is done; releasing discards anything unpublished.

Publish is mandatory: the session ends after the server's idle limit (about 30 minutes) and takes unpublished edits with it. Keep the session open until Step 6b is done; release it after.

### Step 6b: Visual check and fix pass (MANDATORY)

Mentor's self-check has repeatedly reported "all items pass" on screens with visible defects. Look at the live screen yourself before reporting.

1. **Screenshot the live screen** from the runtime URL at desktop width (plus a phone width if the design has one), with whatever browser tool the harness has (e.g. `agent-browser`, Playwright, a browser MCP). Save it as `rendered-r<revision>.png` in the working folder. With no browser tool, ask the user for a screenshot.
   - **Screens that need login:** don't change the screen's access to get a screenshot. Ask the user to sign in, in a headed browser session you can then use, or to send a screenshot.
2. **Compare it with the design, region by region:** structure and placement; typography hierarchy; colours and surfaces; real data values (dates, numbers and their formats); charts actually drawn (lines, bars, no stray axes); default block content replaced (breadcrumbs, tabs); no wrapping, overflow or clipped columns; no chrome the design doesn't have.
3. **List the defects for the user**: for each, what's wrong, what the design shows, and the likely cause. Ask whether to fix them.
4. **On a yes, send one targeted fix turn on the same session**: the batch prompt, then only the listed defects with concrete values (classes, sizes, exact text). It must not publish. Poll it to terminal, **confirm the publish with the user**, publish (Step 6), then screenshot and compare again.
5. **At most two fix passes.** Whatever is still wrong after that is reported as a remaining Mentor-fidelity gap, not looped on.

### Step 7: Report to the user (3–5 lines)

- App name + `app_key`
- Entity / screen counts (from the spec)
- Mentor turn count + build duration (from `duration_ms` / publish timestamps)
- Runtime URL (markdown link)
- The Step 6b result: screenshot path(s), defects fixed, defects left
- Working folder path, and: *"Send another prompt on the same Mentor session for refinements, or open a new session on this app later."*

## Data shape contract

The `spec.json` schema lives in `assets/enriched-blueprint.json`. Top-level keys:

- `name`, `description`, `primary_color`
- `app_chrome`: sidebar nav groups + header content, defined once, shared across all authenticated screens. Login / LayoutBlank screens set `layout_override` and skip `app_chrome`.
- `blocks`: reusable Web Blocks for patterns used on **multiple screens**. Single-screen components live inline in the screen's `anatomy`, not here.
- `design_system`: the **complete token set** (colors AND spacing/radius/shadow scales AND typography roles), plus `visual_rules` and `theme_extensions` (the single source of truth for custom CSS / the app.css the anatomy references).
- `entities`: only the entities the app lacks (for an existing app, reuse its entities by name).
- `sample_data`: the seed set (design's real values, one array per entity) plus the KPI-source store (e.g. a `DashboardMetric` single-row entity). Wired to a short, idempotent, When-Published seed that uses the generated `Create<Entity>` actions (see Step 5). See the schema comment.
- `screens[]`: each with `title`, `subtitle`, an **`anatomy`** (the per-screen widget-tree, the single structural + visual source of truth, Step 3.0), optional `popups[]`, `permissions`.
- `icon_mapping`, `roles`, `acceptance_checklist` (includes the composition-fidelity gates; see Step 3d).

The **`anatomy`** is the per-screen structure (there is no separate `main_content[]`): a nested tree of real OS UI blocks with inline real classes (layout/color/bg/typography), `bind`/`source` on data nodes, `series` on chart nodes, and inline behavior annotations (`onClick`/`onChange`). Store it as an **array of strings, one line of the tree per entry** (the same for a block's `anatomy` in `blocks[]`), never as one escaped string: the user has to be able to read it at the Step 4 review. See `references/design-capture.md` for the format and a worked example.

## Working folder

- Location: `design-to-app/<APP_NAME>/` inside the user's current workspace. Never write under the home folder.
- Retention: the user owns it; nothing expires.
- Contents: `spec.json` (the single authored artifact), `extraction.md` (Figma / HTML / image / code notes), `mentor-batch-<N>.json` (terminal responses), `publish-log.json`.
- Re-running with the same spec: skip Step 3 and go straight to the Step 4 go/no-go.

## Troubleshooting

### Mentor and MCP errors
Handle errors by `data.category` as the main `outsystems` skill describes (`AuthError`, `ValidationError`, `UpstreamError`, `InternalError`, `CapacityError`, and the `tenant_not_allowed` allowlist gate). For a `ValidationError` on a batch prompt, fix the spec slice and resend it on the same session.

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
| Chrome (search / theme toggle / notification badge) missing after publish | Chrome edits only implied in the screen batch | Include the SHARED CHROME paragraph of the batch prompt (Step 5); chrome gets skipped when not named |
| Mentor replies with a plan and "Shall I proceed?", applying nothing | Mentor treated the batch as a planning request | The batch prompt already says to apply now; if it still asks, answer on the same session: "Yes, apply all changes now, do not ask again, and do NOT publish" |
| The first publish fails at the draft-save step on a new app | App was cloned from the built-in default template (outdated OS UI / Charts / Maps pins) | Create the app from the tenant's "Template Web App" (Step 1), or have the user create it in ODC Studio and load it |

### Figma extraction
- Root `get_design_context` returns metadata XML for complex screens: parse child node IDs and batch `get_design_context` on children in **pairs of 2** (4+ concurrent calls cause timeouts).
- If `get_variable_defs` returns empty, extract colors from the design-context code.
- Skip decorative nodes (vectors, masks, lines < 50px). Filter to frames > 100×50.

## Anti-patterns: do NOT do these

The main `outsystems` skill's rules apply. Skill-specific:

- **Don't skip the block-mapping pass (Step 3a).** It's the single biggest source of fake UI when omitted.
- **Don't write Tailwind class names on anatomy nodes.** Figma extracts Tailwind; the anatomy uses OutSystems CSS variables and utility classes (translate hex/px read from Tailwind into OS UI classes/vars).
- **Don't generalize extracted hex codes** (`#EDF0ED` to `#FFFFFF`). If cards use `#EDF0ED` but the page uses `#FFFFFF`, those are DIFFERENT tokens.
- **Don't write block primitives as a styled `<Container>` in the anatomy.** A progress bar written as `<Container class="height-8">` makes the agent build a div; use the real block node (`<ProgressBar …/>`).
- **Don't fire Mentor without user confirmation (Step 4), and don't create an app or publish without confirming that specific write.** An expensive, slow, not-cheaply-reversible build shouldn't happen on assumption.
- **Don't skip or rewrite the batch prompt (Step 5).** It's a field-tested instruction that prevents Mentor from planning instead of building, stopping mid-build or skipping acceptance items.
- **Don't open a second Mentor session mid-build.** A new session starts from the app as last published and carries none of the first session's unpublished edits.
- **Don't edit a System-module template app as the shell.** `Template_*` / `template_*` / `OutSystems Sample Data` are rejected by Mentor's Model API. Clone a new app from the tenant's "Template Web App" instead (Step 1).
- **Don't load all reference docs at once.** Start with the default load set (Step 2), then load on demand based on what the design contains.
- **Don't skip the `references/gotchas/` checklist for visual-source builds.** Eleven specific engine-level traps (SVG icon baking, theme class collisions, SPA visibility toggles, TableRecords empty Source, duplicate primary actions, etc.) are documented in `references/gotchas/INDEX.md`. Each maps a specific source pattern to its fix.

## Related skills

- **`outsystems-spec-driven-build`**: when there's no design source, just a structured spec. Same Mentor invocation pattern, different upstream.
- **`outsystems-app-architecture`**: visualize what was built (interactive HTML graph of screens / actions / entities).

Workflow: design-to-app (build and publish) → app-architecture (visualize what was built).
