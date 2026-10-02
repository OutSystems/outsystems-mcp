---
name: osui-widgets
description: Cross-cutting reference for OutSystems UI widgets and blocks — the semantic widget hierarchy (block → AdvancedHtml → platform widget → Container), full anti-pattern table, polish gates, default-children-to-strip table, Entities enums, Form input widgets catalog, and Quick lookup by requirement. Load this for OS UI domain knowledge before reaching into a specific patterns/<category>.md file.
---

# OutSystems UI — Widgets & Blocks Reference

The single cross-cutting reference for OS UI domain knowledge. Use this to pick the right widget / block / pattern and to validate spec composition. For deep block-by-block detail (args + placeholders + events), drop into the matching `patterns/<category>.md`.

> Stack note: OutSystems UI uses its own CSS variables on `:root` (`--color-primary`, `--space-base`, …). Customize via theme StyleSheet variable overrides — see [`styles-and-utilities.md`](styles-and-utilities.md).

> ⚠️ **Naming note:** Widget JSON `type_` values use the `Mobile` prefix historically (`IMobileScreen`, `IMobileBlockInstanceWidget`, `IMobileFlow`, …) — the prefix applies to BOTH Reactive Web AND Mobile UI Template. There is no `IReactiveBlockInstanceWidget`.

## Semantic widget hierarchy (non-negotiable)

Every visual element on the screen needs to be expressed as a **real, semantically-meaningful widget** — never as a styled `Container` + custom CSS pretending to be UI. Pretending produces "fake UI" that's invisible to assistive tech, fragile under theme changes, and looks plausible in screenshots but is non-functional.

For each element, walk the hierarchy top → down and use the first option that fits:

### 1. **OutSystems UI block** — first choice when a block exists

If an OS UI block matches the requirement (Carousel, Tabs, Card, Counter, Tag, Alert, Sidebar, Wizard, Breadcrumbs, Pagination, Dropdown, DatePicker, …), spec it as a block instance. See the anti-pattern table below + the matching `patterns/*.md`.

### 2. **`AdvancedHtml` with a semantic HTML5 tag** — preferred fallback when no block fits

OutSystems' platform widget `AdvancedHtml` (`Object: "AdvancedHtml"` in widget JSON) lets you set the HTML element via its `Tag` property. **Use this for any structural element with a real HTML5 equivalent** — semantic markup, free accessibility roles, theme-friendly CSS targeting:

| Need | Use `AdvancedHtml` with `Tag` = |
|---|---|
| Page header / app header strip | `"header"` |
| Sidebar / aside panel content | `"aside"` |
| Top-level navigation region | `"nav"` |
| Self-contained content section | `"section"` |
| Standalone article-like block (e.g. a transaction row, a card body without `Card` block) | `"article"` |
| Page footer | `"footer"` |
| Headings | `"h1"` / `"h2"` / `"h3"` / `"h4"` / `"h5"` / `"h6"` |
| Paragraph of text | `"p"` |
| Unordered / ordered list | `"ul"` / `"ol"` (and `"li"` for items) |
| Description list | `"dl"` (and `"dt"` / `"dd"`) |
| Inline emphasis | `"strong"` / `"em"` |
| Time / date | `"time"` |
| Figure with caption | `"figure"` (and `"figcaption"`) |

`AdvancedHtml` accepts text content (via `TextWidget` children) and other widgets. It's a real platform widget — not custom CSS.

### 3. **Platform interactive widgets** — for interactivity without an OS UI block

Use a built-in platform widget: `Button`, `Link`, `Input`, `TextArea`, `Form`, `Image`, `Icon`, `Text`, `If`, `List` / `TableRecords`. Full catalog + purpose in the [Form input widgets (built-in, not blocks)](#form-input-widgets-built-in-not-blocks) section below.

These are real interactive widgets with proper events, accessibility, and validation. Don't replace them with `Container` + click handlers.

### 4. **`Container`** — only when truly nothing else fits

A `Container` renders as `<div>`. Reach for it when (a) the element is purely a positioning / grouping wrapper with no semantic meaning, AND (b) no Layout helper (`Columns2`, `Columns3`, `AlignCenter`, etc.) expresses the layout you need. If you're styling a `Container` to LOOK like something (a card, a button, a banner, a section heading) — **stop**, you almost certainly want option 1, 2, or 3.

### Red-flag heuristic

If your screen's `StyleSheet` contains CSS rules with class names that imply structural identity — `.card`, `.banner`, `.sidebar`, `.tabs`, `.carousel`, `.button`, `.header`, `.footer` — the design lost the right widget somewhere. Re-architect: replace that CSS with the matching block / `AdvancedHtml` / platform widget.

### Always-block primitives (no exceptions, regardless of design precision)

Some elements **must** go through the OS UI block / platform widget. CSS approximations are wrong even when the design source provides exact pixel specs. The list:

| Element | Block / widget | Why CSS is never the answer |
|---|---|---|
| Buttons / clickable actions | `IButton`, `ILink` | Focus states, keyboard activation, ARIA, validation, disabled-state styling |
| Charts (donut / bar / line / area) | `DonutChart`, `BarChart`, `LineChart`, `AreaChart` (+ `ChartLegend`, `ChartSeriesStyling`) | Highcharts under the hood, theme-aware, accessible, responsive — a `<div>` with `conic-gradient` / styled bars is none of these |
| Carousels / horizontally-scrolling card stacks | `Carousel` block | Swipe, keyboard nav, pagination dots wired in, mobile-correct — CSS overflow-x is broken on touch and on resize |
| Icons | `IIcon` (Phosphor name + `IconSize=FontSize`) | Theme-color tinting, typography scale, a11y; emoji and `Container`-as-circle-stub are not icons |
| Inputs (text / date / number / dropdown / textarea / checkbox / switch / radio) | `Input`, `Dropdown`, `TextArea`, `Checkbox`, `Switch`, `RadioGroup` | Validation, labels via `Label.TargetWidget`, mandatory marker, type-aware keyboards on mobile |
| Avatars (image / initials / circle silhouette) | `UserAvatar` block | Initials fallback, theme-aware, image sizing handled |
| Progress bars (used / total) | `ProgressBar` block from `OutSystemsUI/Numbers` | `Progress`, `Thickness`, `OptionalConfigs` (record literal) — CSS track-and-fill divs lose all of it |
| Status pills / badges | `Tag` block | Theme color variants, sizing, rounded variants — not a styled `Container` |
| Repeating data rows | `IList` + `IListItem` + `ListItemContent` | Keyboard nav, swipe-actions, mocked-source path via LocalVariable + `ListLiteral` when no entity exists |

**`Container` + custom CSS remains valid** for: hero gradients / decorative banners, wave-pattern overlays on cards, positioning wrappers, one-off visual ornaments that don't fit any block. The decision rule isn't "always blocks" — it's "use the block whenever a block exists for the role."

### Figma / design-source pixel specs are CONSTRAINTS, not implementation

When you have precise pixel values (widths, hex codes, radii, shadows, gradients) from a Figma file or design spec, **do NOT translate them directly into `Container` + `CustomStyle: "width: 298px; background: linear-gradient(...)"`**. The pixel spec describes the target — the implementation goes through the block + theme + extended class:

- Hex color → theme variable override (`--color-primary` etc.) on the THEME's StyleSheet, applied via the block's normal styling
- Gradient → a single CSS class defined once on the theme StyleSheet, applied via `ExtendedClass="card-coral"` on the matching `Card` block — never inlined per element via `CustomStyle`
- Radius / shadow / padding → block default args (`Card.UsePadding`) + utility classes (`border-radius-soft`, `padding-l`) + theme variable; only fall back to `CustomStyle` for the genuinely-bespoke flourish that no block expresses
- Width / height → block sizing args + responsive utility classes; literal `width: 298px` is rarely justified

Specifically: precise Figma values for a card-shaped, button-shaped, chart-shaped, carousel-shaped, or progress-bar-shaped region map to the corresponding block from the table above — even when the spec is exact down to the pixel.

### Anti-pattern table (catch yourself BEFORE writing widget JSON)

**Block fallbacks** (block exists for this — use it):

| If you're tempted to write… | STOP. Use this instead |
|---|---|
| `Container` styled with horizontal-scroll CSS, holding cards | `Carousel` block + `Card` blocks |
| Two `Container`s toggled by `IsActiveTab` LocalVariable | `Tabs` + `TabsHeaderItem` + `TabsContentItem` |
| `Container` with `box-shadow` + `border-radius` + padding mimicking a card | `Card` block | [`patterns/content.md#card`](patterns/content.md#card) |
| Hand-rolled list of `Link`/`Container` items in `LayoutSideMenu.Navigation` or `LayoutTopMenu.Header` | `Menu` block (from `Common`) wrapping the placeholder, with `Link` widgets inside `Menu.PageLinks` |
| Raw `Link`s placed directly in `Navigation` / `Header` placeholders (no `Menu` wrapper) | `Menu` block first, then `Link`s inside `Menu.PageLinks` |
| `Container` with `OnClick`, styled to look like a button | `Button` widget |
| `Container` with icon + heading + dismiss × pretending to be a notice | `Alert` (inline) or `Notification` (toast) |
| `<h1>` + `<small>` styled as a stat box | `Counter` block, often inside `Columns3` |
| Three `Container`s with `flex: 1` for a 3-column row | `Columns3` block (responsive collapse via `BreakColumns`) | [`patterns/adaptive.md`](patterns/adaptive.md) |
| Hand-rolled chip / pill container next to text | `Tag` block | [`patterns/content.md#tag`](patterns/content.md#tag) |
| Manual avatar circle (image + border-radius CSS) | `UserAvatar` block | [`patterns/content.md#useravatar`](patterns/content.md#useravatar) |
| Emoji as an icon (`🏠 Home`, `💳`, `📧`) inside text widgets | `IIcon` widget with a Phosphor name (`house`, `credit-card`, `envelope`) and `IconSize=FontSize` | — |
| `Container` with `border-radius: 50%` + colored background as a fake icon stub | `IIcon` widget with a Phosphor name; tint via `text-primary` / `text-success` etc. | — |
| `Style` or `Width` set on the `Menu`'s `PageLinks` container — or a `Container` wrapper between PageLinks and the Links | Add `ILink` widgets DIRECTLY to PageLinks; don't style the container |
| Custom CSS variable names (`--bg-deep`, `--accent`) scoped to a wrapper class (`.dark-mode { … }`) for theming the app — written on a SCREEN's StyleSheet | Override the EXISTING OS UI variables (`--color-neutral-0`–`-10`, `--color-primary`, `--color-background-body`, `--color-text-primary`) at `:root` on the THEME's StyleSheet | [`styles-and-utilities.md#theming-the-app-dark-mode-full-rebrand-palette-swap`](styles-and-utilities.md#theming-the-app-dark-mode-full-rebrand-palette-swap) |
| `LayoutBlank` + a custom flex shell on the screen StyleSheet (`.app { min-height: 100vh; display: flex }`, `.sidebar { width: 240px; position: sticky }`, `.main { flex: 1; overflow-y: auto }`) for a "highly custom" design | `LayoutSideMenu` (or `LayoutTopMenu`) + theme variable overrides for the visuals. The layout owns the shell, the theme owns the colors. | [`layouts.md#when-the-design-feels-too-custom-for-a-layout-block-the-dark-mode-trap`](layouts.md#when-the-design-feels-too-custom-for-a-layout-block-the-dark-mode-trap) |
| Avatar built as `Container` with `border-radius: 50%` + linear-gradient background + initials text widget | `UserAvatar` block (`Name`, `Image`, `Size`, `Color`, `Shape`, `ExtendedClass`) |
| Notification badge as `Container` with `position: absolute; top: -4px; right: -4px; background: red; border-radius: 50%` overlaid on a bell icon | `IconBadge` block from `OutSystemsUI/Numbers` with the icon in the `Icon` placeholder |
| Flex-column of `<div class="tx-row">` divs with hardcoded transaction content | `IList` over a screen aggregate + `IListItem` + `ListItemContent` block per row (Left / Title / Content / Right placeholders) |
| Custom CSS donut (`background: conic-gradient(...)` with a hole div in the middle) | `DonutChart` block from `OutSystemsCharts/Charts` + `ChartLegend` addon |
| Custom progress bar (`<div class="track"><div class="fill" style="width: 68%">`) | `ProgressBar` block from `OutSystemsUI/Numbers` (`Progress`, `Thickness`, `OptionalConfigs`) |
| **Project-prefix custom class** applied to a `Container` (e.g. `Style="hb-stat-card"`, `Style="my-app-tile"`, `Style="<prefix>-<role>"`) | The underlying `Container` is the wrong widget — spec the matching OS UI block (`Card`, `CardItem`, `Tag`, `UserAvatar`, etc.) and pass one-off visual treatment via the block's `ExtendedClass` argument |
| **Class name applied without a matching CSS definition** in the theme StyleSheet / screen StyleSheet / block StyleSheet | Either define the class (in the theme if cross-screen, screen StyleSheet if scoped) OR spec a real OS UI block + utility classes. Undefined class references are silent no-ops — visual treatment never appears |
| **Removing a chart block when no real aggregate exists** + replacing with a custom CSS donut / placeholder div | Mock `DataPointList` with `ExpressionDefinition.ListLiteral` of `RecordLiteral`s (literal Label/Value/Color) — keeps the real chart with all its theme/legend/animation behavior |
| **Removing an `IList` when no entity matches the prompt** + replacing with a flex-column of hardcoded `<div>` rows | Probe `OutSystemsSampleData` first (`Sample_Transaction`, `Sample_Employee`, `Sample_Product`, …); if no match fits, mock the source via a LocalVariable populated with `ListLiteral` of `RecordLiteral`s in `OnInitialize`. **Always keep the real `IList` + `IListItem` + `ListItemContent` blocks** — never hand-roll fake rows |
| Sliding panel with overlay backdrop | `Sidebar` or `BottomSheet` | [`patterns/interaction.md`](patterns/interaction.md) |
| Click-to-expand collapsible section | `Accordion` + `AccordionItem` | [`patterns/content.md#accordion`](patterns/content.md#accordion) |

**Semantic-HTML fallbacks** (no block fits — use `AdvancedHtml` with the right tag, NOT a styled `Container`):

| If you're tempted to write… | STOP. Use this instead |
|---|---|
| `Container Style="\"page-header\""` styled to look like a banner header | `AdvancedHtml Tag="header"` with the title widgets inside |
| `Container Style="\"sidebar-aside\""` for an aside panel | `AdvancedHtml Tag="aside"` |
| `Container Style="\"navigation-rail\""` for a nav region | `AdvancedHtml Tag="nav"` (with `Menu` / `MenuItem` blocks inside if it's the app menu) |
| `Container Style="\"section-wrapper\""` to group related content | `AdvancedHtml Tag="section"` |
| `Container Style="\"transaction-row\""` for a self-contained item | `AdvancedHtml Tag="article"` (or `CardItem` block if it fits) |
| `Container Style="\"page-footer\""` at the bottom of the screen | `AdvancedHtml Tag="footer"` |
| Plain text in a `Container` with `font-size: 24px` + `font-weight: bold` | `AdvancedHtml Tag="h1"` … `Tag="h6"` |
| Long-form copy inside a `Container` | `AdvancedHtml Tag="p"` |
| List of bullet items as separate `Container`s | `AdvancedHtml Tag="ul"` containing `AdvancedHtml Tag="li"` items |

The semantic tag gives you accessibility roles (`<nav>` is announced as navigation, `<header>` and `<aside>` map to landmarks), free CSS targeting (`nav { … }` works without a class name), and visual consistency with the OS UI theme.

Custom `Container` + CSS is only justified when (a) no block fits AND (b) no HTML5 element semantically describes the region. That's a small set: positioning wrappers, grouping for `Columns*` cells, styling adjusters with no semantic meaning.

## Building a screen? START HERE

Two ordered steps before you write a single widget. Skipping either is the #1 cause of "fake UI" output (custom-container scaffolds, no Cards, no Columns).

**Step A — Pick the Layout, THEN delete the default before adding it.** Load [`layouts.md`](layouts.md) and pick `LayoutSideMenu`, `LayoutTopMenu`, or `LayoutBlank` based on the screen's navigation pattern. **Don't default to `LayoutBlank`** — that gives you nothing. ⚠️ **Before adding your chosen Layout, delete the default `LayoutTopMenu` that `CreateScreen` ships with** — see [`layouts.md#before-you-add-any-layout--delete-the-default-one-the-screen-ships-with`](layouts.md#before-you-add-any-layout--delete-the-default-one-the-screen-ships-with) for the inspect-delete-add code pattern. Skipping the delete is the #1 cause of "two layouts at the screen root" regressions even when the agent correctly picked a single Layout.

**Step B — Sketch the structural skeleton + commit to a block inventory.** Answer two questions for the content of each Layout placeholder: *what is the column grid?* and *what are the card surfaces?* The output is a tree of `Columns*` and `Card` family blocks with no `Container` nodes. Then complete the **block-inventory commitment** — explicit "this region → that block" mapping for EVERY visual region, BEFORE writing any widget JSON. **Do this before loading any `patterns/*.md`** — pattern files only help once the skeleton is in place AND the block inventory is committed. Without the inventory, design pressure pushes the agent into "Container + custom CSS class" mode.

Only AFTER both steps, fill the skeleton:
- The matching OS UI block for each sub-element (Carousel, Tabs, sidebar Menu, Alert, Counter, Buttons) — see the anti-pattern table above + the relevant `patterns/*.md`.
- `AdvancedHtml` with the right HTML5 tag for everything else with semantic meaning (see hierarchy above).

## Finishing a screen? DON'T STOP YET

A "valid" screen with no polish reads as a wireframe. Bake these gates into the spec's `acceptance_checklist`:

1. Delete every block's default children (Tabs ships with 3 placeholder tabs, Carousel with a default List, etc.).
2. Apply typography hierarchy (`h1` for screen title, `h2` for section headings, `h3` for card titles, `strong` for inline emphasis).
3. Use brand color sparingly (2–3 deliberate uses per screen, on the most important affordances).
4. Add spacing between sections via OS UI utility classes (`margin-top-xl` etc.), NOT custom CSS.
5. Populate with realistic placeholder content (3–4 currency cards, 4–5 transactions, real names, masked PANs).
6. Make one element clearly the visual focal point (don't let everything have the same weight).
7. Section headings are `AdvancedHtml Tag="h2"`, never plain `Text` or styled `Container`.

**These polish acceptance items are mandatory in every spec.**

## Task → file

| Task | Load |
|---|---|
| Pick the right Layout block + understand its placeholders | [`layouts.md`](layouts.md) |
| Pick a block by requirement / look up its arguments / placeholders / events | This file's "Need a specific pattern" + matching `patterns/<category>.md` |
| Pick a utility class (spacing / color / typography / flex / shadow / radius) / look up a CSS variable / theme the app | [`styles-and-utilities.md`](styles-and-utilities.md) |
| **Theme the app — dark mode, brand recolor, full palette swap** (override OS UI CSS variables on the THEME's StyleSheet, never on a screen's, never with invented variable names) | [`styles-and-utilities.md#theming-the-app-dark-mode-full-rebrand-palette-swap`](styles-and-utilities.md#theming-the-app-dark-mode-full-rebrand-palette-swap) |

## Need a specific pattern? Load the matching category file

| Looking for… | Load | Flow (in `OutSystemsUI` reference) |
|---|---|---|
| Cards, sections, alerts, accordion, tags, tooltips, avatars, blank state | [`patterns/content.md`](patterns/content.md) | `Content` |
| Date pickers, dropdowns, sliders, sidebars, sheets, carousels, gestures | [`patterns/interaction.md`](patterns/interaction.md) | `Interaction` |
| Tabs, wizards, breadcrumbs, pagination, timelines, app navigation | [`patterns/navigation.md`](patterns/navigation.md) | `Navigation` |
| KPI counters, badges, progress indicators, ratings | [`patterns/numbers.md`](patterns/numbers.md) | `Numbers` |
| Column layouts, gallery, master-detail, device-aware rendering | [`patterns/adaptive.md`](patterns/adaptive.md) | `Adaptive` |
| AlignCenter, Separator, gestures, small layout helpers | [`patterns/utilities.md`](patterns/utilities.md) | `Utilities` |

### Local-app blocks (NOT in `OutSystemsUI`)

These live in the **app's own flows**, not under the OutSystems UI reference:

| Block | Where |
|---|---|
| `LayoutSideMenu`, `LayoutTopMenu`, `LayoutBlank`, etc. | App's `Layouts` flow |
| `Menu`, `MenuItem` (app's nav) | App's `Common` flow |

### Placeholder naming in the spec

Use the **full path** form: `<BlockName>.<PlaceholderName>` — e.g., `Tabs.Header`, `Card.Content`, `Carousel.CarouselItems`.

## Default children to strip (acceptance item per block)

Many blocks ship with placeholder children for the design-time editor. When populating programmatically, defaults remain alongside what you add — **spec must instruct Mentor to delete defaults first**. Skipping this is the #1 source of "phantom empty cards / tabs / steps" rendering in front of real content.

| Block | Default child | In placeholder |
|---|---|---|
| `Carousel` | One `IList` widget | `Carousel.CarouselItems` |
| `Tabs` | Three `TabsHeaderItem` + three `TabsContentItem` instances | `Tabs.Header` and `Tabs.Content` |
| `Wizard` | A few `WizardStep` instances | `Wizard.Steps` |
| `Accordion` | A few `AccordionItem` instances | `Accordion.AccordionItems` |
| `BottomBar` / `Navigation` blocks | Default item placeholders | (varies) |
| `Button` / `Link` | Default text child | Widget's own children |

Add an acceptance-checklist item per block instance: *"Delete default children from `<Block>.<Placeholder>` before adding new widgets."*

**ExtendedClass is additive** — a node's `class=` in the anatomy (the block's ExtendedClass) is appended to the block's default class, never overwrites. The default carries load-bearing styling (`btn` on Button, the visual-treatment class on Card/Tag/Tabs, active/inactive on TabsHeaderItem). Replacing it strips focus rings, padding, transitions, and visual contract.

## Reference entities (enums)

Used as values for many block arguments. Reference as `Entities.<Name>.<Value>`:

| Entity | Values |
|---|---|
| `Entities.Color` | `Primary`, `Secondary`, `Transparent`, `Neutral0`–`Neutral10`, `Red`, `Orange`, `Yellow`, `Lime`, `Green`, `Teal`, `Cyan`, `Blue`, `Indigo`, `Violet`, `Grape`, `Pink` |
| `Entities.Position` | `Center`, `Top`, `Bottom`, `Left`, `Right`, `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight` |
| `Entities.Orientation` | `Horizontal`, `Vertical` |
| `Entities.Direction` | `Right`, `Left` |
| `Entities.Size` | `Small`, `Medium` |
| `Entities.Shape` | `Rounded`, `Sharp`, `SoftRounded` |
| `Entities.Space` | `None`, `ExtraSmall`, `Small`, `Base`, `Medium`, `Large`, `ExtraLarge`, `XXLarge` |
| `Entities.GutterSize` | Same values as `Space`, distinct enum — use for column gaps |
| `Entities.Trigger` | `Hover`, `Click` (used by `Tooltip.Trigger`) |
| `Entities.BreakColumns` | `None`, `All`, `First` (column collapse behavior per breakpoint) |
| `Entities.Alert` | `Success`, `Error`, `Info`, `Warning` |
| `Entities.Speed` | `Slow`, `Normal`, `Fast` |
| `Entities.AnimationType` | `TopToBottom`, `BottomToTop`, `LeftToRight`, `RightToLeft`, `FadeIn`, `Scale`, `ScaleDown`, `Bounce`, `Spinner` |
| `Entities.Gradient` | `LinearHorizontal`, `LinearVertical`, `LinearDiagonally`, `Radial` |
| `Entities.AccordionIconType` | `Caret`, `PlusMinus`, `Custom` |
| `Entities.CarouselNavigation` | `Arrows`, `Dots`, `Both`, `None` |
| `Entities.StackedOptions` | `Bottom`, `Top`, `None` |
| `Entities.Steps` | `Past`, `Active`, `Next` (Wizard step status) |
| `Entities.DatePickerTimeFormat` | `Time24hFormat`, `Time12hFormat`, `Disabled` |

## Form input widgets (built-in, not blocks)

These are native OutSystems widgets, not OutSystems UI blocks:

| Widget | Purpose |
|---|---|
| `Button` / `Link` | Action triggers (`OnClick` → ScreenAction) |
| `Input` | Single-line text/date/number input (`Variable`, `InputType`, `Mandatory`) |
| `TextArea` | Multi-line input |
| `Checkbox` | Boolean toggle |
| `RadioButton` / `RadioGroup` | Single-choice |
| `Switch` | On/off toggle |
| `Dropdown` | Select from list (`Source` bound to aggregate `.List`) |
| `Upload` | File upload |
| `Form` | Validation container (includes `OnSaveClick` action with `Form1.Valid` check) |
| `Label` | Field label (use `TargetWidget` to point to its Input's `Name`) |
| `List` / `ListItem` | Repeating container bound to `Source = <Aggregate>.List` |
| `TableRecords` | Tabular data with `headerRow` + `row` arrays |
| `Container` | Generic block-level wrapper |
| `IfWidget` | Conditional rendering (`Condition`, `TrueBranch`, `FalseBranch`) |
| `TextWidget` | Static text |
| `Expression` | Bound text from a variable or expression |
| `Icon` | Icon glyph |
| `ImageWidget` | Image |
| `AdvancedHtml` | Custom HTML tag (use `Tag: "h1"` for screen titles) |

### Popup widget (built-in, not a UI block)

`Popup` is a native widget (not an OS UI block instance). Toggled via a Boolean LocalVariable bound to `ShowPopup`. Use `Style: "\"popup-dialog\""` for the standard modal look.

## Quick lookup by requirement

| Requirement keyword | Block(s) |
|---|---|
| FAQ / collapsible | `Accordion` + `AccordionItem` |
| empty / no-results | `BlankSlate` |
| toast / notification | `Notification` (auto-dismiss) or `Alert` (inline) |
| confirmation modal | `Popup` (native widget) |
| date picker | `DatePicker` / `DatePickerRange` / `MonthPicker` / `TimePicker` |
| dropdown with search | `DropdownSearch` |
| multi-select dropdown | `DropdownTags` or `DropdownServerSide_MultipleSelection` |
| infinite-scroll dropdown | `DropdownServerSide_WithOnScrollEnding` |
| carousel / slideshow | `Carousel` |
| sidebar / drawer | `Sidebar` |
| bottom sheet | `BottomSheet` |
| FAB / speed dial | `FloatingActions` |
| swipe cards (Tinder) | `StackedCards` |
| video | `Video` |
| image lightbox | `LightBoxImage` |
| pagination | `Pagination` (bound to a paginated aggregate) |
| tabs | `Tabs` + `TabsHeaderItem` + `TabsContentItem` |
| wizard / steps | `Wizard` + `WizardItem` |
| breadcrumbs | `Breadcrumbs` + `BreadcrumbsItem` |
| timeline | `TimelineItem` |
| star rating | `Rating` |
| progress bar | `ProgressBar` (linear) / `ProgressCircle` (radial) |
| badge / chip | `Tag` (chip) / `Badge` (numeric) / `IconBadge` (overlay on icon) |
| user avatar | `UserAvatar` |
| tooltip | `Tooltip` |
| chat bubble | `ChatMessage` |
| flip card | `FlipContent` |
| floating panel | `FloatingContent` |
| product card grid | `Gallery` (with `IList` + `Card`/`CardSectioned`) |
| master/detail layout | `MasterDetail` |
| device-specific content | `DisplayOnDevice` |
| 2/3/N column layout | `Columns2`–`Columns6` (or `ColumnsSmall*` / `ColumnsMedium*` for asymmetric) |
| swipe gestures | `SwipeEvents` |
| inline SVG | `InlineSVG` |
| visual divider | `Separator` |
| centered content | `AlignCenter` (1D) / `CenterContent` (with top/center/bottom zones) |
| button with spinner | `ButtonLoading` |

## Critical rules

1. **`Gallery` content must wrap a `List`** for aggregate-bound data. `Gallery → Content → List → Card`.
2. **`Counter` has only ONE placeholder** (`Counter.Content`). Put icon, value, and label all inside it. No separate `Value`/`Label`/`Icon` placeholders.
3. **Block instances don't accept `Width`, `Style`, `Margin`, or `CustomStyle`** directly. To style a block, wrap it in a `Container`.
4. **Tabs / Accordion / Wizard / Breadcrumbs / SectionIndex / SectionGroup / Submenu** require their child item blocks (`TabsHeaderItem`, `AccordionItem`, etc.) inside specific named placeholders.
5. **`Pagination` requires `StartIndex` + `MaxRecords` LocalVariables** bound to its source aggregate. The `OnNavigate` handler must update `StartIndex` and refresh the aggregate.
6. **Toggle pattern** for ActionSheet, BottomSheet, Notification, Sidebar, Popup: `IsOpen`/`StartsOpen` Boolean LocalVariable + a `Toggle*` ScreenAction that assigns `not <variable>` + the block's visibility argument bound to that variable.

## What NOT to load

- **All pattern category files at once.** Load only the category that matches the task.

## Token budget shape

```
top-level SKILL.md                ← pipeline + anatomy-first spec format
  ↓
this ui-reference.md                   ← OS UI cross-cutting reference (load here for hierarchy / anti-patterns / Quick lookup)
  ↓
ONE leaf doc                      ← layouts / styles-and-utilities / patterns/<category> / charts / maps / design-tokens
```

If you find yourself loading 3+ leaf docs in a single task, you're probably over-fetching — re-read this router and pick the smallest set.
