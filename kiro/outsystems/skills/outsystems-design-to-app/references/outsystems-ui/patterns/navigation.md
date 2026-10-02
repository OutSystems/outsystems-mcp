---
name: osui-navigation-patterns
description: OutSystems UI navigation patterns — Tabs, Wizard, Breadcrumbs, Pagination, BottomBarItem, SectionIndex, Submenu, TimelineItem. Use when adding tabbed views, multi-step flows, paginated lists, breadcrumb trails, or app navigation.
---

# Navigation Patterns

> **Category:** Navigation — moving around within or between screens.
> **Module:** OutSystemsUI

Patterns covered: `BottomBarItem`, `Breadcrumbs`, `BreadcrumbsItem`, `Pagination`, `SectionIndex`, `SectionIndexItem`, `Submenu`, `Tabs`, `TabsHeaderItem`, `TabsContentItem`, `TimelineItem`, `Wizard`, `WizardItem`.

For format conventions (FULL PATH parameters, required `Arguments: []` and `PlaceholdersContent: []`), see `../ui-reference.md`.

## Requirement → block

| Requirement | Block(s) |
|---|---|
| Switch between sibling views on one screen | `Tabs` + `TabsHeaderItem` + `TabsContentItem` |
| Multi-step ordered flow | `Wizard` + `WizardItem` |
| Breadcrumb trail on a detail screen | `Breadcrumbs` + `BreadcrumbsItem` |
| Page through a long list | `Pagination` (with paginated aggregate) |
| Side anchor links to scroll to sections | `SectionIndex` + `SectionIndexItem` |
| Mobile bottom-bar navigation | `BottomBarItem` (one per tab) |
| Collapsible nested menu group | `Submenu` |
| Vertical event/activity timeline | `TimelineItem` |

## Tabs + TabsHeaderItem + TabsContentItem

Tabbed switcher between 2–6 sibling content panels.

**`Tabs` arguments**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Tabs.StartingTab` | Integer | `0` | Zero-based index of the active tab on initial render. |
| `Tabs.TabsOrientation` | `Entities.Orientation` | `Horizontal` | `Horizontal` or `Vertical`. |
| `Tabs.TabsVerticalPosition` | `Entities.Direction` | `Left` | When vertical: `Left` or `Right`. |
| `Tabs.OptionalConfigs` | Record | `{}` | `{ JustifyHeaders: Boolean }` to stretch headers across width. |
| `Tabs.Height` | Text (CSS) | `""` | Fixed height for content area; empty = auto. |
| `Tabs.ExtendedClass` | Text | `""` | Extra CSS. |

**`Tabs` placeholders**

| Placeholder | Contents |
|---|---|
| `Tabs.Header` | One `TabsHeaderItem` per tab, in order. |
| `Tabs.Content` | One `TabsContentItem` per tab, **same order** as headers. |

**`Tabs` events**

| Event | Payload | Purpose |
|---|---|---|
| `Tabs.OnTabChange` | `ActiveTab` (Integer) | Fires when active tab changes. Pass via FULL PATH: `Parameter: "Tabs.OnTabChange.ActiveTab"`. |
| `Tabs.Initialized` | `TabsId` (Text) | Fires when the block finishes initializing. |

**`TabsHeaderItem`**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `TabsHeaderItem.IsDisabled` | Boolean | `False` | Disables the tab. |
| `TabsHeaderItem.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `TabsHeaderItem.Title` | Tab label (text + optional icon). |

**`TabsContentItem`**

| Parameter | Type | Purpose |
|---|---|---|
| `TabsContentItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `TabsContentItem.Content` | The tab body. |

**Composition**

- Header item count MUST equal content item count and they must be in the same order. Index 0 of headers maps to index 0 of content.
- Programmatically switch tabs by calling `<TabsBlock>.SetActiveTab(NewIndex)` from a ScreenAction or by binding `StartingTab` to an Integer LocalVariable updated by `OnTabsChange`.
- Avoid nesting `Tabs` inside `Tabs` — restructure into separate screens or use a sidebar.
- Don't use `Tabs` for ordered/sequential steps — use `Wizard`.


## Wizard + WizardItem

Step indicator for multi-step flows. **`Wizard` is a visual indicator only** — the actual step navigation buttons live elsewhere on the screen and update a `CurrentStep` LocalVariable.

**`Wizard` arguments**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Wizard.IsVertical` | Boolean | `False` | Vertical step list (mobile/sidebar) vs horizontal strip. |
| `Wizard.ExtendedClass` | Text | `""` | Extra CSS. |

**`Wizard` placeholders**

| Placeholder | Contents |
|---|---|
| `Wizard.Content` | One or more `WizardItem` children. |

**`WizardItem`**

| Parameter | Type | Purpose |
|---|---|---|
| `WizardItem.Status` | `Entities.Steps` | `Past` (done) · `Active` (current) · `Next` (upcoming). |
| `WizardItem.UseTopLabel` | Boolean | Place label above icon (vs beside). |
| `WizardItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `WizardItem.Icon` | Step number or icon. |
| `WizardItem.Label` | Step title. |

**Composition**

- Track current step in a LocalVariable (`CurrentStep` Integer, default `1`).
- Drive each item's `Status` from `CurrentStep`:
  ```
  If(CurrentStep > N, Entities.Steps.Past,
    If(CurrentStep = N, Entities.Steps.Active,
       Entities.Steps.Next))
  ```
- Step navigation buttons (Next/Previous) update `CurrentStep` and conditionally render the relevant step content (an `IfWidget` chain on the same screen).

## Breadcrumbs + BreadcrumbsItem

Hierarchical link chain shown above the screen title.

**`Breadcrumbs`**

| Parameter | Type | Purpose |
|---|---|---|
| `Breadcrumbs.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Breadcrumbs.Content` | One or more `BreadcrumbsItem` children. |

**`BreadcrumbsItem`**

| Parameter | Type | Purpose |
|---|---|---|
| `BreadcrumbsItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `BreadcrumbsItem.Title` | Link (intermediate crumb) or `TextWidget` (current page, last crumb). The separator icon between crumbs is rendered automatically by the parent `Breadcrumbs` block. |

**Composition**

- Place at the top of `MainContent` (or in the layout's `Breadcrumbs` placeholder if it has one).
- Last crumb is plain text, no link.

## Pagination

Page-through controls for a paginated `ScreenAggregate`.

**Arguments**

| Parameter | Type | Purpose |
|---|---|---|
| `Pagination.StartIndex` | Integer | Current offset — bind to a LocalVariable matching the aggregate's `StartIndex`. |
| `Pagination.MaxRecords` | Integer | Page size — bind to a LocalVariable matching the aggregate's `MaxRecords`. |
| `Pagination.TotalCount` | Integer expression | Total rows — bind to `<Aggregate>.Count`. |
| `Pagination.ShowGoToPage` | Boolean | Renders the "page X of Y" input + counter row alongside the prev/next buttons. Even when the design doesn't show these elements, **leave this `True`** and hide them via CSS (`.pagination-input, .pagination-counter { display: none }`) — see "Styling the buttons" below. |
| `Pagination.ExtendedClass` | Text | Extra CSS. Applied to the block's root, NOT to the buttons. |

**Placeholders**

| Placeholder | Contents |
|---|---|
| `Pagination.Previous` | The icon shown inside the prev button. Default is a chevron. Replace with your own `IIcon` (Phosphor `caret-left` / `arrow-left` etc.) to swap the glyph. **Delete the default first.** |
| `Pagination.Next` | Same as Previous, but for the next button. |

> ⚠️ **These placeholders ONLY swap the icon glyph.** They do NOT let you restyle the button chrome (background, border, shape, size). The icon you place lives INSIDE the block's own `.pagination-button` element — whatever `ExtendedClass` you put on a wrapper Container around the icon is sealed inside that button and cannot recolor it. To recolor / reshape / resize the buttons themselves, use CSS targeting `.pagination-button` directly — see "Styling the buttons" below.

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Pagination.OnNavigate` | `NewStartIndex` (Integer) | User clicked Prev/Next/page #. Handler must `Assign(StartIndex = NewStartIndex)` and `RefreshDataNode` the aggregate. Pass with FULL PATH: `Parameter: "Pagination.OnNavigate.NewStartIndex"`. |
| `Pagination.Initialized` | `PaginationId` (Text) | Fires when block initializes. |

**Composition**

- The aggregate MUST have `MaxRecords` and `StartIndex` set to LocalVariables (not literals) so refresh repaginates correctly.
- Place `Pagination` immediately below the data widget (`TableRecords`, `IList`, `Gallery`).
- For server-side dropdowns with infinite scroll, use `DropdownServerSide_WithOnScrollEnding` instead of Pagination.

**OnNavigate handler shape**

```
StartNode → AssignNode { StartIndex = NewStartIndex } → RefreshDataNode <Aggregate> → EndNode
```

### Styling the buttons (icon-only prev/next, custom colors, hidden input/counter)

When the design shows just two prev/next buttons — no page-number input, no "1 of 12" counter, and the buttons themselves have a custom background / border / shape — placeholder content alone is not enough. The block's rendered DOM has three styleable surfaces:

| Selector | What it controls |
|---|---|
| `.pagination-button` | The prev/next BUTTON chrome — background, border, border-radius, padding, hover state. The Previous/Next placeholders sit inside this. |
| `.pagination-input` | The "Go to page" numeric input. Hide when not in the design. |
| `.pagination-counter` | The "X of Y" page counter text. Hide when not in the design. |

**Canonical pattern** — apply via the theme's StyleSheet (or scoped via `Pagination.ExtendedClass` + a wrapper selector if the visual is truly screen-local):

```css
/* Hide the input + counter — keep only the prev/next buttons */
.pagination-input,
.pagination-counter { display: none; }

/* Restyle the prev/next chrome — 36×36 circles, etc. */
.pagination-button {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  border: none;
  background: var(--color-neutral-2);
  color: var(--color-text-secondary);
}

/* Per-side styling — use :first-of-type / :last-of-type on .pagination-button
   to color prev vs next differently (e.g., neutral prev, brand-green next).
   Inspect the rendered DOM to confirm the selector — block-internal class
   names can vary across OS UI versions. */
.pagination-button:last-of-type {
  background: var(--color-primary);
  color: var(--color-text-primary);
}
```

**Spec-side declaration** — in a design-to-app spec, declare these in `design_system.theme_extensions.classes[]` (each rule body emitted as-is onto the theme StyleSheet, NOT wrapped in `.<name>{}`):


The selector lives in the rule body (`.pagination-button { … }`), NOT in the class name — the rule emits raw into the StyleSheet and targets the block's internal DOM directly. The `Pagination.ExtendedClass` arg can still be used for ROOT-level adjustments (margins, alignment), but it does not reach inside `.pagination-button`.

**Don't try to** wrap the `IIcon` in a Container with classes like `arrow-prev` / `arrow-next` and expect that to restyle the button — the wrapper Container is INSIDE `.pagination-button`, and the button's own styling wins. CSS targeting `.pagination-button` is the only way.

## SectionIndex + SectionIndexItem

Sticky side-anchor navigation that scrolls the page to a target widget.

**`SectionIndex`**

| Parameter | Type | Purpose |
|---|---|---|
| `SectionIndex.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `SectionIndex.Content` | One or more `SectionIndexItem` children. |

**`SectionIndexItem`**

| Parameter | Type | Purpose |
|---|---|---|
| `SectionIndexItem.ScrollToWidgetId` | Text | The `Name` of the target widget on the page. |
| `SectionIndexItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `SectionIndexItem.Content` | Anchor label. |

**Composition**

Place `SectionIndex` in a sidebar column (e.g. `ColumnsSmallRight.Column2`) beside the main content. Each target section needs a unique `Name`.

## Submenu

Collapsible navigation group (typically used inside a Menu Block).

| Parameter | Type | Purpose |
|---|---|---|
| `Submenu.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Submenu.Menu` | The trigger label (icon + text). |
| `Submenu.Items` | `Link` widgets for each child option. |

## TimelineItem

A single chronological event. Stack multiple `TimelineItem` blocks vertically — there is no `Timeline` parent block.

| Parameter | Type | Purpose |
|---|---|---|
| `TimelineItem.Color` | `Entities.Color` | Color of the timeline dot. |
| `TimelineItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `TimelineItem.Left` | Date or label shown to the left of the dot. |
| `TimelineItem.Icon` | Icon inside the dot. |
| `TimelineItem.Title` | Event title. |
| `TimelineItem.Content` | Event description. |
| `TimelineItem.Right` | Action icon / button. |

For a data-bound timeline, render `TimelineItem` inside an `IList` over a chronological aggregate.

## BottomBarItem

A single tab in a mobile bottom navigation bar. There is no `BottomBar` parent block — wrap multiple `BottomBarItem` blocks inside a `Container` styled as a bottom bar.

| Parameter | Type | Purpose |
|---|---|---|
| `BottomBarItem.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `BottomBarItem.Icon` | Tab icon. |
| `BottomBarItem.Text` | Tab label. |

**Composition**

- Each `BottomBarItem` is wrapped in a `Link` (or `Button`) with `Width: "(fill parent)"`. The Link's `OnClick` navigates to the target screen.
- Apply `Style: "\"active\""` to the currently selected item's Link.

## Cross-cutting rules

1. **Order matters in Tabs and Wizard.** Header item N maps to content item N, and `WizardItem` order defines step sequence.
2. **`Pagination` has `Previous` and `Next` placeholders that only swap the icon glyph** — they do NOT let you restyle the button chrome. To recolor / reshape the buttons, target `.pagination-button` via CSS (and hide `.pagination-input` / `.pagination-counter` if the design omits them). See "Styling the buttons" above.
3. **`Pagination` requires aggregate-level binding.** The aggregate's `StartIndex`/`MaxRecords` must be LocalVariables, and `OnNavigate` must update both and refresh.
4. **Wizard is visual only.** It doesn't render or hide step content — gate that yourself with `IfWidget(CurrentStep = N)`.
5. **`SectionIndex` requires `Name` on each target widget.** The `ScrollToWidgetId` matches the widget's `Name` exactly.
6. **Event parameters use FULL PATH format too** — e.g. `Parameter: "Tabs.OnTabChange.ActiveTab"`, `Parameter: "Pagination.OnNavigate.NewStartIndex"`.

## Accessibility notes

- `Tabs` headers have `role="tab"`, content panels have `role="tabpanel"`. Arrow keys cycle, Enter/Space activates. Don't replace the header item with a non-button widget.
- `Breadcrumbs` is rendered as a `<nav>` with `aria-label="breadcrumb"`. Mark the current page (last crumb) as plain text, not a link.
- `Pagination` renders Prev/Next as `<button>` elements (class `.pagination-button`) internally and disables them at boundaries automatically. The icon inside each button can be swapped via `Pagination.Previous` / `Pagination.Next` placeholders; the button chrome itself is restyled via CSS on `.pagination-button`.
- `Wizard` step status is conveyed visually and via `aria-current` on the active step. Tooltip step labels for icon-only steps.
- `BottomBarItem` should be wrapped in `<a>` (Link), not `<div>`, for proper keyboard navigation.
