---
name: osui-navigation-patterns
description: OutSystems UI navigation patterns — Tabs, Wizard, Breadcrumbs, Pagination, BottomBarItem, SectionIndex, Submenu, TimelineItem. Use when adding tabbed views, multi-step flows, paginated lists, breadcrumb trails, or app navigation.
---

# Navigation Patterns

> **Category:** Navigation — moving around within or between screens.
> **Module:** OutSystemsUI

Patterns covered: `BottomBarItem`, `Breadcrumbs`, `BreadcrumbsItem`, `Pagination`, `SectionIndex`, `SectionIndexItem`, `Submenu`, `Tabs`, `TabsHeaderItem`, `TabsContentItem`, `TimelineItem`, `Wizard`, `WizardItem`.

For the widget hierarchy and `Entities` values, see `../ui-reference.md`.

## Requirement → block

| Requirement | Block(s) |
|---|---|
| Switch between sibling views on one screen | `Tabs` + `TabsHeaderItem` + `TabsContentItem` |
| Multi-step ordered flow | `Wizard` + `WizardItem` |
| Breadcrumb trail on a detail screen | `Breadcrumbs` + `BreadcrumbsItem` |
| Page through a long list | `Pagination` (with paginated aggregate) |
| Side anchor links to scroll to sections | `SectionIndex` + `SectionIndexItem` |
| Mobile bottom-bar navigation | Part of the mobile app layout (`BottomBarItem`), not a screen block — see [BottomBarItem](#bottombaritem) |
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
| `Tabs.OnTabChange` | `TabsId` (Text), `ActiveTab` (Integer) | Fires when active tab changes. |
| `Tabs.Initialized` | `TabsId` (Text) | Fires when the block finishes initializing. |

**`TabsHeaderItem`**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `TabsHeaderItem.ExtendedClass` | Text | `""` | Extra CSS. (No `IsDisabled` input.) |

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
- To switch tabs from logic, bind `StartingTab` to an Integer local variable and update it in `OnTabChange`.
- Avoid nesting `Tabs` inside `Tabs` — restructure into separate screens or use a sidebar.
- Don't use `Tabs` for ordered/sequential steps — use `Wizard`.


## Wizard + WizardItem

Step indicator for multi-step flows. **`Wizard` is a visual indicator only** — the actual step navigation buttons live elsewhere on the screen and update a `CurrentStep` local variable.

**`Wizard` arguments**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Wizard.IsVertical` | Boolean | `False` | Vertical step list (mobile/sidebar) vs horizontal strip. |
| `Wizard.StepsBehaviour` | Identifier | — | Step behaviour option; leave the default unless the design needs otherwise. |
| `Wizard.ExtendedClass` | Text | `""` | Extra CSS. |

**`Wizard` placeholders**

| Placeholder | Contents |
|---|---|
| `Wizard.Content` | One or more `WizardItem` children. |

**`WizardItem`**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `WizardItem.Status` | `Steps` Identifier (required) | — | `Past` (done) · `Active` (current) · `Next` (upcoming). |
| `WizardItem.ReverseLabelPosition` | Boolean | `False` | Swap the label to the other side of the icon. |
| `WizardItem.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `WizardItem.Icon` | Step number or icon. |
| `WizardItem.Label` | Step title. |

Event `WizardItem.OnClick` — user clicked the step.

**Composition**

- Track current step in a local variable (`CurrentStep` Integer, default `1`).
- Drive each item's `Status` from `CurrentStep`:
  ```
  If(CurrentStep > N, Entities.Steps.Past,
    If(CurrentStep = N, Entities.Steps.Active,
       Entities.Steps.Next))
  ```
- Step navigation buttons (Next/Previous) update `CurrentStep` and conditionally render the relevant step content (an `If` chain on the same screen).

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
| `BreadcrumbsItem.Title` | `Link` (intermediate crumb) or `Text` (current page, last crumb). The separator between crumbs is rendered automatically by the parent `Breadcrumbs` block. |
| `BreadcrumbsItem.Icon` | Optional icon before the crumb. |

**Composition**

- Place at the top of `MainContent` (or in the layout's `Breadcrumbs` placeholder if it has one).
- Last crumb is plain text, no link.

## Pagination

Page-through controls for a paginated screen aggregate.

**Arguments**

| Parameter | Type | Purpose |
|---|---|---|
| `Pagination.StartIndex` | Integer | Current offset — bind to a local variable matching the aggregate's `StartIndex`. |
| `Pagination.MaxRecords` | Integer | Page size — bind to a local variable matching the aggregate's `MaxRecords`. |
| `Pagination.TotalCount` | Integer expression | Total rows — bind to `<Aggregate>.Count`. |
| `Pagination.ShowGoToPage` | Boolean | Default `False`. Set `True` only when the design shows a "go to page" input. |
| `Pagination.ExtendedClass` | Text | Extra CSS. Applied to the block's root, NOT to the buttons. |

**Placeholders**

| Placeholder | Contents |
|---|---|
| `Pagination.Previous` | The icon shown inside the prev button. Default is a chevron. Replace with your own `Icon` (Phosphor `caret-left` / `arrow-left` etc.) to swap the glyph. **Delete the default first.** |
| `Pagination.Next` | Same as Previous, but for the next button. |

> ⚠️ **Glyph rule: these placeholders ONLY swap the icon glyph.** They do NOT restyle the button chrome (background, border, shape, size) — the icon lives INSIDE the block's own button, so an `ExtendedClass` on a wrapper Container around the icon cannot recolor it. To restyle the prev/next buttons, see "Styling the buttons" below.

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Pagination.OnNavigate` | `NewStartIndex` (Integer) | User clicked Prev/Next/page #. The handler assigns `StartIndex = NewStartIndex`, then refreshes the aggregate. |
| `Pagination.Initialized` | `PaginationId` (Text) | Fires when block initializes. |

**Composition**

- The aggregate MUST have `MaxRecords` and `StartIndex` set to local variables (not literals) so refresh repaginates correctly.
- Place `Pagination` immediately below the data widget (`TableRecords`, `List`, `Gallery`).

### Styling the buttons (icon-only prev/next, custom colors)

When the prev/next buttons have a custom background / border / shape, restyle them with a custom rule defined in `theme_extensions`. **Scope every rule to the `.pagination-previous` / `.pagination-next` wrappers** — a bare `.pagination-button` rule also restyles every page-number button.

```css
/* Restyle only the prev/next chrome — 36×36 circles, etc. */
.pagination-previous .pagination-button,
.pagination-next .pagination-button {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  border: none;
  background: var(--color-neutral-2);
  color: var(--color-neutral-8);
}

/* Per-side styling — e.g. neutral prev, brand next */
.pagination-next .pagination-button {
  background: var(--color-primary);
  color: var(--color-neutral-0);
}
```

The selector lives in the rule body and targets the block's internal DOM directly. `Pagination.ExtendedClass` can still be used for ROOT-level adjustments (margins, alignment), but it does not reach inside the buttons.

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

Collapsible navigation group (typically used inside a Menu block).

| Parameter | Type | Purpose |
|---|---|---|
| `Submenu.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Submenu.Menu` | The trigger label (icon + text). |
| `Submenu.Items` | `Link` widgets for each child option. |

Event `Submenu.OnToggle` — fires when the group expands or collapses.

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

For a data-bound timeline, render `TimelineItem` inside a `List` over a chronological aggregate.

## BottomBarItem

A single tab in a mobile app's bottom navigation bar. It belongs to the mobile app layout (the bottom bar the layout renders), not to an individual screen's anatomy — there is no `BottomBar` block, and don't hand-build one from a styled `Container` on a screen.

## Cross-cutting rules

1. **Order matters in Tabs and Wizard.** Header item N maps to content item N, and `WizardItem` order defines step sequence.
2. **`Pagination.Previous` / `Next` only swap the icon glyph** — see the glyph rule under [Pagination](#pagination).
3. **`Pagination` requires aggregate-level binding.** The aggregate's `StartIndex`/`MaxRecords` must be local variables, and `OnNavigate` must update `StartIndex` and refresh.
4. **Wizard is visual only.** It doesn't render or hide step content — gate that yourself with an `If` (`CurrentStep = N`).
5. **`SectionIndex` requires `Name` on each target widget.** The `ScrollToWidgetId` matches the widget's `Name` exactly.

## Accessibility notes

- `Tabs` headers have `role="tab"`, content panels have `role="tabpanel"`. Arrow keys cycle, Enter/Space activates. Don't replace the header item with a non-button widget.
- `Breadcrumbs` is rendered as a `<nav>` with `aria-label="breadcrumb"`. Mark the current page (last crumb) as plain text, not a link.
- `Pagination` renders Prev/Next as `<button>` elements internally and disables them at boundaries automatically.
- `Wizard` step status is conveyed visually and via `aria-current` on the active step. Tooltip step labels for icon-only steps.
