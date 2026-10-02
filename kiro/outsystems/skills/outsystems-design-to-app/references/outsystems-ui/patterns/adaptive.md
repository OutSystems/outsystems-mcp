---
name: osui-adaptive-patterns
description: OutSystems UI adaptive layout patterns — Columns2-6, ColumnsMediumLeft/Right, ColumnsSmallLeft/Right, DisplayOnDevice, Gallery, MasterDetail. Use when building responsive multi-column layouts, device-aware content, card grids, or split views.
---

# Adaptive Patterns

> **Category:** Adaptive — device-aware layout primitives.
> **Module:** OutSystemsUI

Patterns covered: `Columns2`, `Columns3`, `Columns4`, `Columns5`, `Columns6`, `ColumnsMediumLeft`, `ColumnsMediumRight`, `ColumnsSmallLeft`, `ColumnsSmallRight`, `DisplayOnDevice`, `Gallery`, `MasterDetail`.

For built-in screen layout placeholders (`Header`, `MainContent`, `Title`, etc.), see [`layouts.md`](../layouts.md). For utilities like `AlignCenter` and `Separator`, see [`utilities.md`](./utilities.md).

## Requirement → block

| Requirement | Block |
|---|---|
| 2/3/4/5/6 equal columns | `Columns2`, `Columns3`, `Columns4`, `Columns5`, `Columns6` |
| 60/40 split, wider left | `ColumnsMediumLeft` |
| 40/60 split, wider right | `ColumnsMediumRight` |
| 33/67 split, narrower left | `ColumnsSmallLeft` |
| 67/33 split, narrower right | `ColumnsSmallRight` |
| Show different content per device | `DisplayOnDevice` |
| Responsive product/card grid (1–8 per row) | `Gallery` |
| List-pane / detail-pane split view | `MasterDetail` |

## All Column blocks share the same arguments

`Columns2`, `Columns3`, `Columns4`, `Columns5`, `Columns6`, `ColumnsMediumLeft`, `ColumnsMediumRight`, `ColumnsSmallLeft`, `ColumnsSmallRight`:

| Parameter | Type | Purpose |
|---|---|---|
| `Columns*.GutterSize` | `Entities.GutterSize` | Gap between columns. Values: `None`, `ExtraSmall`, `Small`, `Base`, `Medium`, `Large`, `ExtraLarge`, `XXLarge`. |
| `Columns*.PhoneBehavior` | `Entities.BreakColumns` | How columns collapse on phone. Values: `None` (keep side-by-side), `All` (stack all vertically), `First` (only the first column breaks to full width). |
| `Columns*.TabletBehavior` | `Entities.BreakColumns` | Same enum, applied at tablet breakpoint. |
| `Columns*.ExtendedClass` | Text | Extra CSS. |

> The enum is `Entities.GutterSize` (not `Entities.Space`) for column gaps — even though the values match `Space`. Use `Entities.GutterSize.Base`, etc.

**Placeholders** are `Column1`, `Column2`, … up to the column count. Asymmetric variants:

| Block | `Column1` size | `Column2` size |
|---|---|---|
| `ColumnsSmallLeft` | narrow (~33%) | wide (~67%) |
| `ColumnsSmallRight` | wide (~67%) | narrow (~33%) |
| `ColumnsMediumLeft` | wide (~60%) | narrow (~40%) |
| `ColumnsMediumRight` | narrow (~40%) | wide (~60%) |

**Composition**

- Use Column blocks as the OUTER structure of any multi-column section. Don't use raw HTML or CSS grid.
- Set `PhoneBehavior = Entities.BreakColumns.All` for desktop-first layouts that must stack on phones. `Entities.BreakColumns.None` keeps them side-by-side; `First` breaks only the first column to full width.
- Don't set `Width`, `Style`, or `Margin` on the column block itself — those properties are silently dropped on `IMobileBlockInstanceWidget`. To style, wrap in a `Container`.


## DisplayOnDevice

Renders different content per device class. Each placeholder shows ONLY on its target device.

**Arguments:** none.

| Placeholder | Renders on |
|---|---|
| `DisplayOnDevice.OnDesktop` | Desktop. |
| `DisplayOnDevice.OnTablet` | Tablet. |
| `DisplayOnDevice.OnPhone` | Phone. |

**Use for** truly different layouts per device. **Don't use for** simple responsive reflow — Column blocks handle that.

Omit a placeholder to render nothing on that device.


## Gallery

Responsive item grid. Auto-distributes children into rows based on the per-device row size.

| Parameter | Type | Purpose |
|---|---|---|
| `Gallery.RowItemsDesktop` | Integer (`1`–`8`) | Items per row on desktop. |
| `Gallery.RowItemsTablet` | Integer | Items per row on tablet. |
| `Gallery.RowItemsPhone` | Integer | Items per row on phone (often `1`). |
| `Gallery.ItemsGap` | Text token | Gap between items. Quoted string token name: `"\"none\""`, `"\"xs\""`, `"\"s\""`, `"\"base\""`, `"\"m\""`, `"\"l\""`, `"\"xl\""`, `"\"xxl\""`. |
| `Gallery.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Gallery.Content` | The items. **For data-bound galleries, this MUST contain an `IList`.** |

**Critical pattern** — when items come from an aggregate:

```
Gallery
└─ Content
   └─ IList (Source = <Aggregate>.List)
      └─ <Card> / <CardSectioned> / etc.
         └─ Bound expressions on .List.Current.<Entity>.<Attribute>
```

For static items (e.g., a fixed set of features), put the widgets directly in `Gallery.Content` without an `IList`.

**Don't** put cards directly in `Gallery.Content` when the data is dynamic — the grid won't know to repeat them.


## MasterDetail

Side-by-side list/detail on desktop, drill-down on phone.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `MasterDetail.Height` | Text (CSS) | `""` | Fixed height (e.g. `"\"500px\""`); empty = auto. |
| `MasterDetail.LeftPercentage` | Decimal | `40` | Left pane width as % of total (desktop). |
| `MasterDetail.OpenedOnPhone` | Boolean | `False` | When `True`, the detail pane is shown on phone (drill-down state). |

| Placeholder | Contents |
|---|---|
| `MasterDetail.LeftContent` | List pane (typically a search + `TableRecords`/`IList`). |
| `MasterDetail.RightContent` | Detail pane (typically a Form or read-only detail). |

**Event** `MasterDetail.DetailClose` — fires when user dismisses the detail pane on phone. Handler should `Assign(OpenedOnPhone = False)`.

**Composition**

- On phone tap of a list item, set `OpenedOnPhone = True` to slide in the detail.
- The detail pane re-uses the same `OpenedOnPhone` LocalVariable to show a back button.
- Bind `RightContent` widgets to a `SelectedId` LocalVariable that is set when the user picks a list item.

## Cross-cutting rules

1. **Column blocks are layout structure, not content.** Use them for the outer skeleton; put `Card`/`Counter`/etc. inside.
2. **Gallery + IList is the canonical card-grid pattern** for data-bound layouts. `IList` alone (no Gallery) gives you a vertical list, not a grid.
3. **Don't combine `DisplayOnDevice` with `IfWidget(IsPhone())`** for the same content — pick one approach. `DisplayOnDevice` is purely visual; `IsPhone()` lets you branch behavior, too.
4. **`MasterDetail.LeftPercentage`** only applies on desktop/tablet — phone collapses to drill-down regardless.
5. **`UIBlockInstanceWidget` properties don't include `Width`/`Style`/`Margin`/`CustomStyle`.** Wrap in a `Container` to apply those.

## Accessibility notes

- Column blocks expose semantic `<section>` elements. Don't replace them with `<div>` via `ExtendedClass`.
- `DisplayOnDevice` server-side renders only the matching device's content — no client-side hidden DOM. Screen readers see only what's rendered, which is correct.
- `Gallery` items rendered through `IList` should have meaningful focusable elements (Link/Button) for keyboard navigation.
- `MasterDetail` traps focus inside the detail pane on phone when open. Don't break this with custom focus management.
