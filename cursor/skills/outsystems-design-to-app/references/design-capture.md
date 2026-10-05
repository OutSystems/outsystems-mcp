# Design Capture — author the screen as a widget-tree ANATOMY (inside `spec.json`)

**The core artifact is a per-screen `anatomy`: a nested widget tree of real OutSystems UI blocks with the visual styles inline.** You author it directly inside each screen in `spec.json`. `spec.json` is the single authored artifact and the exact contract sent to Mentor.

**Why an anatomy, not prose:** see SKILL.md Step 3.0. In short, Mentor only sees the spec text, and an explicit widget tree leaves it little to reinterpret.

## Workflow: consult the OS UI blocks FIRST, then compose the anatomy

1. **Read the OS UI block references before composing.** You must build the anatomy from *real* blocks with their *real* inputs, placeholders, and classes — never invented ones. Consult the skill's own `references/outsystems-ui/*` (patterns, `ui-reference.md`, `styles-and-utilities.md`). For each region of the design, find the block that matches (Card, Columns*, Gallery, Table, ProgressBar, TimelineItem, Tag, UserAvatar, Breadcrumbs, DatePickerRange, DropdownSearch, AreaChart/LineChart/BarChart, …) and read its real inputs and placeholders. Use `styles-and-utilities.md` as the utility-class reference: a class that isn't listed there is either a custom class you must define in `theme_extensions`, or a typo.
2. **Compose the screen's widget-tree anatomy** from those blocks — nested, with the visual styles inline as real classes, plus data bindings and chart series (below).
3. **Define custom classes once** in `design_system.theme_extensions` (the app.css) — any class the anatomy references that isn't a stock OS utility.

## What the anatomy MUST capture (every visual aspect)

- **Real OS UI blocks** as the nodes (from the KB), correctly **nested** (which block, in which parent placeholder).
- **Layout & sizing** — grids/columns (`Columns*`, `ColumnsMediumLeft`, `ColumnsSmallRight`, `Gallery`; a named exact-ratio class only as Step 3a's exception 2), gaps, padding, heights, widths — as real utility classes or a declared custom class.
- **Colors & backgrounds** — per node: `background-*`, `text-*`, border, brand accent, chart series colors.
- **Typography** — per node: heading/eyebrow/metric/body roles as real classes.
- **Data bindings** — `bind=`/`source=` naming the entity/attribute (render the VALUE, never a literal path).
- **Chart config** — explicit `series=[…]` + colors + `axes=hidden legend=hidden` etc. (no flat/degenerate charts). The series/`DataPointList` MUST resolve to a **populated aggregate over a seeded entity** (or a parsed metric field) — never a declared-but-empty list variable. Field-tested: charts bound to an empty `DataPointList` render nothing.
- **Custom classes** referenced here are DEFINED in `design_system.theme_extensions` (emitted once onto the theme).

## Format — a per-screen `anatomy` (pseudo-JSX), stored in `spec.json`

Real OSUI block names, `class=` carrying real utility + custom classes, `bind=`/`series=` for data. Rough is fine — it's a structure+style contract, not compilable code.

**How it's stored:** in `spec.json` the `anatomy` is an **array of strings, one line of the tree per entry**, indentation kept (`"anatomy": ["<LayoutTopMenu>", "  <Header>…</Header>", …]`). Never write it as one string with escaped `\n`: it turns a 7 KB tree into a single unreadable line, and the user reviews this file at the go/no-go. When you send the spec to Mentor, the array is fine as-is.

Worked example (Console / Overview), shown here as plain text:

```jsx
{/* StatRow and DeltaBadge are NOT OutSystems UI blocks: they are this app's own reusable
    Web Blocks, declared once in spec.blocks[] (inputs: Label/value/Delta/trend/LineColor).
    Everything else below is a real OS UI block or widget. */}
<LayoutTopMenu>
  <Header><Menu ActiveItem=0 links=["Overview*","Records","Board","Reports","New record"] brand="Console" login="right" class="console-topnav"/></Header>

  <Breadcrumbs>
    {/* sanctioned exception 1: inline alignment inside ONE placeholder */}
    <Container class="page-toolbar display-flex align-items-center gap-base justify-content-space-between">
      <Container class="display-flex align-items-center gap-s">
        <Breadcrumbs items=["Home","Overview"]/>
        <Tag Color=Green IsLight Shape=Rounded>Live · auto-refresh on</Tag>
      </Container>
      <Container class="toolbar-right display-flex gap-s align-items-center">
        <DatePickerRange class="date-w" value="21 Jul 2026 to 19 Aug 2026"/>
        <DropdownSearch source="Category.Name" prompt="All categories" class="toolfield-w"/>
        <Button class="btn btn-primary">New record</Button>
      </Container>
    </Container>
  </Breadcrumbs>

  <MainContent class="page-canvas">                                    {/* applies background: var(--page-bg) */}
    {/* HERO band: 62/38 split inside one themed container (divider between) */}
    <Card UsePadding=false class="margin-bottom-base">
      <Container class="console-hero">                                   {/* sanctioned exception 2: named exact-ratio class */}
        <Container class="padding-m">
          <Container class="display-flex align-items-center gap-s margin-bottom-base">
            <Text class="eyebrow">RECORDS PROCESSED</Text>
            <Tag Color=Primary IsLight Shape=Rounded>Rolling 30d</Tag>
          </Container>
          <Container class="display-flex align-items-flex-end gap-base">
            <Container class="metric-xl" bind="DashboardMetric.RecordsProcessed">135</Container>
            <DeltaBadge class="margin-bottom-s" percent="+42.5%" caption="vs previous 30d"/>
          </Container>
          <Container class="margin-top-base hero-chart">
            <AreaChart Height=128px Spline series=[8,10,9,12,11,14,13,16,15,18,17,22] seriesColor="#6D3BEB" lineWidth=3 axes=hidden legend=hidden spacing=0/>
            <Container class="display-flex justify-content-space-between gap-s font-size-xs text-neutral-5"><Text>21 Jul</Text><Text>17 Aug</Text></Container>
          </Container>
        </Container>
        <Container class="stack">                                        {/* right column, divided rows */}
          <StatRow Label="ACTIVE"        bind="DashboardMetric.ActiveCount"   value=92   Delta="+43.2%" trend=[70,74,79,83,88,92]  LineColor="#0F9D63"/>
          <StatRow Label="HIGH PRIORITY" bind="DashboardMetric.HighPriority"  value=45   Delta="+58.8%" trend=[20,28,32,38,42,45]  LineColor="#D2453E"/>
          <StatRow Label="AVG. CYCLE"    bind="DashboardMetric.AvgCycleDays"   value=15.6 unit="days" Delta="±0" trend=[15.5,15.6,15.6,15.5,15.6,15.6] LineColor="#8B95A4"/>
        </Container>
      </Container>
    </Card>

    {/* PIPELINE HEALTH — ONE row inside one Card: label | segmented strip | legend (inline alignment, exception 1) */}
    <Card class="padding-base margin-bottom-base">
      <Container class="display-flex align-items-center gap-l">
        <Container class="pipeline-label"><Text class="eyebrow">PIPELINE HEALTH</Text><Text class="num font-semi-bold font-size-xs">94% within SLA</Text></Container>
        <BarChart class="seg-strip flex1" Height=28px pointWidth=14px spacing=0 stacked=100% horizontal series=[{On track:46,#0F9D63},{In review:23,#6D3BEB},{At risk:11,#E8892B},{Breached:5,#D2453E},{Closed:11,#8B95A4}]/>
        <Container class="pipeline-legend display-flex gap-base font-size-xs text-neutral-6">{/* legend: dot+label+pct per status */}</Container>
      </Container>
    </Card>

    {/* MAIN + RAIL */}
    <ColumnsMediumRight GutterSize=Base
      Column1={
        <Card UsePadding=false>
          <Container class="card-head display-flex justify-content-space-between align-items-center"><Text class="heading3">Recent records</Text><Text class="num text-neutral-6 font-size-xs">8 shown · View all</Text></Container>
          <Table source="Record⋈Category⋈Status sort=CreatedOn desc max=8">
            <Column head="CODE"><Expression class="num text-neutral-5" bind="Record.Code"/></Column>
            <Column head="RECORD"><Text class="font-bold" bind="Record.Title"/><Text class="text-neutral-6 font-size-xs" bind="Category.Name"/></Column>
            <Column head="OWNER"><UserAvatar bind="Record.OwnerName"/><Text bind="Record.OwnerName"/></Column>
            <Column head="STATUS"><Tag IsLight Shape=Rounded color="Status.ColorHex" bind="Status.Label"/></Column>
            <Column head="TREND"><LineChart class="row-spark" Height=40px spacing=0 series=[per-row] seriesColor="#6D3BEB" axes=hidden legend=hidden/></Column>
            <Column head="AMOUNT" class="text-align-right"><Expression class="num font-bold" bind="FormatCurrency(Record.Amount, '$', 2, '.', ',')"/></Column>
          </Table>
        </Card>}
      Column2={
        <><Card class="padding-m margin-bottom-base">
            <Container class="display-flex justify-content-space-between align-items-center margin-bottom-base"><Text class="heading3">By category</Text><Text class="eyebrow">SHARE</Text></Container>
            <List source="Category"><Container class="margin-bottom-s"><Container class="display-flex justify-content-space-between gap-s font-size-xs"><Text bind="Category.Name"/><Expression class="num font-bold" bind="Category.SharePct+'%'"/></Container><ProgressBar class="thinbar" Progress="Category.SharePct" ProgressColor=Primary Thickness=6/></Container></List>
          </Card>
          <Card class="padding-m">
            <Text class="heading3">Activity</Text>
            <List source="Activity sort=CreatedOn desc"><TimelineItem color="Status.ColorHex" title="Activity.Note" content="Activity.CreatedByName + ' · ' + CreatedOn"/></List>
          </Card></>}
    />
  </MainContent>
</LayoutTopMenu>
```

And the **theme_extensions (app.css)** it references: every custom class in the anatomy above is defined here, once (no dangling class):
```css
:root { --page-bg:#F4F5F7; }
.page-canvas    { background:var(--page-bg); }                     /* the page background, APPLIED */
.console-topnav { border-bottom:1px solid var(--color-neutral-3); }
.page-toolbar   { padding:8px 0; }
.toolbar-right  { flex-wrap:nowrap; }
.date-w         { width:240px; }
.toolfield-w    { width:200px; }
.console-hero   { display:grid; grid-template-columns:62% 38%; }   /* exact-ratio split */
.stack          { border-left:1px solid var(--color-neutral-3); }  /* + row dividers */
.metric-xl      { font:700 48px "Space Grotesk", sans-serif; line-height:1.1; color:var(--color-neutral-10); white-space:nowrap; min-width:3ch; }
.eyebrow        { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--color-neutral-7); white-space:nowrap; }
.num            { font-variant-numeric:tabular-nums; white-space:nowrap; }
.hero-chart     { min-height:128px; }
.pipeline-label { flex:0 0 auto; }
.pipeline-legend{ flex:0 0 auto; white-space:nowrap; }
.seg-strip      { min-height:28px; border-radius:999px; overflow:hidden; } /* widget >=28px; bar thickness via pointWidth */
.card-head      { padding:16px 24px; border-bottom:1px solid var(--color-neutral-3); }
.row-spark      { width:96px; height:40px; }                       /* fixed width so it can't eat the row */
.thinbar        { margin-top:4px; }
```

> **Note on the custom `display:grid` / `display:flex` classes above.** SKILL.md Step 3a forbids CSS flex/grid for **section-level layout** where children are independent blocks — those must be Adaptive blocks (`Columns2`–`Columns6`, `ColumnsMediumRight`, `Gallery`, …). The classes here are the **two sanctioned exceptions**: (1) inline alignment inside a single placeholder (`.page-toolbar`, the pipeline row and its legend) and (2) an **exact-ratio split an Adaptive block can't hit** (`.console-hero` 62/38), allowed ONLY as a **named class defined once in `theme_extensions`** — never inline on the node. Prefer `ColumnsMediumRight`/`Columns2` when the ratio is close enough.

## Two recipes for producing the anatomy
- **A. Reconstruct (image/Figma):** walk the design region-by-region; for each, pick the real block (consult the KB), nest it, and set inline classes read from the pixels (grid/gaps/sizes/colors/type). Transcribe sample values; mark uncertain colors approximate. Modal/scrim images: reconstruct the underlying screen from structure; treat only the crisp modal as exact.
- **B. Extract (TSX/React/HTML — highest fidelity):** the source *is* an anatomy — map its components → OSUI blocks, its classes/constants → tokens + inline classes, its data hooks → bindings, its arrays → series + sample_data.

## KPI-source decision
Headline numbers (135/92/45/15.6) are almost never a live count over the seed → bind them to a stored metric entity (`DashboardMetric`) or seed enough rows. Never `Count()` over 8 rows and expect 135.

## Seeding (runs at deploy, once)
`sample_data` is the seed set; how it is seeded (generated `Create<Entity>` actions, Count guard, When-Published timer, literal values) is SKILL.md Step 5 / rule R3.

## Sizing completeness (this is where "structure right, look wrong" comes from)

Field-tested: an anatomy with correct structure still renders broken when SIZE is under-specified. The three real failures and their rules:

1. **Every custom class the anatomy references MUST be DEFINED in `theme_extensions` — no dangling classes.** A referenced-but-undefined class (e.g. a sparkline width `spark-w`) is a silent no-op: the element is unconstrained, grows to fill, and squeezes its siblings (that is what wrapped a `92` metric onto two lines). Before firing: list every `class=` token in the anatomy and confirm each is either a stock OS utility OR defined in `theme_extensions`.
2. **A background token DEFINED is not APPLIED.** Defining `--page-bg: #F4F5F7` does nothing unless a node actually uses it. **Apply the page background explicitly** — the screen root / MainContent carries `background: var(--page-bg)` (a `.page-canvas` class). Otherwise the canvas falls through to the theme default (which rendered DARK). Same for any surface: define AND apply.
3. **Charts need a render-safe height.** Highcharts reserves ~25px for spacing, so a `12px`–`26px` chart collapses to nothing (that is why the pipeline bar and thin sparklines vanished). Give every chart widget a real height (**≥ 28px**, sparklines ~40px; a thin segmented bar keeps a ≥28px widget and gets its thin look from the bar thickness, ~14px) AND apply the zero-spacing config (`chart.spacingTop/Bottom/Left/Right = 0`) so a short chart uses its whole box.
4. **Pin size-critical dimensions in the anatomy**, don't leave them to chance:
   - metrics/numbers: `white-space:nowrap` + a `min-width` so `92` / `15.6 days` never wrap;
   - sparklines / row charts: a FIXED width class (defined!) so they don't eat the row;
   - grids: real column sizes (`grid-template-columns: 1fr 96px auto`, not three `auto`s that let a chart dominate);
   - inline label pairs: an explicit gap so text doesn't run together ("HomeOverview", "21 Jul17 Aug").

## Verify before firing Mentor (gate)
- The `anatomy` covers the WHOLE screen (every visible region is a node), built from **real OS UI blocks** (you consulted the KB), correctly nested.
- Every node carries its visual styling (layout/size/color/bg/typography) as real classes.
- **Sizing completeness:** every referenced custom class is DEFINED in `theme_extensions` (no dangling class); the page background is APPLIED (light canvas), not just defined; every chart has a render-safe height (≥28px) + zeroed spacing; metrics have `nowrap`/`min-width`; sparklines have a fixed defined width; grids use explicit column sizes.
- Every data node has a `bind`/`source` (a value, never a literal path); every chart has an explicit `series` that resolves to a populated source (not an empty DataPoint list); each KPI has a source decision.
- `sample_data` uses the design's real values; seed is idempotent + short-flow + When-Published, via generated `Create<Entity>` actions.
- Tricky regions map to the correct block (segmented bar → stacked BarChart; sparkline → hidden-axis LineChart; card grid → Gallery), not a raw container.

The composition-fidelity `acceptance_checklist` gates (SKILL.md Step 3d) encode these so Mentor self-verifies during the build.
