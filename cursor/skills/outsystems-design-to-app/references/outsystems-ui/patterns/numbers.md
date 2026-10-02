---
name: osui-numbers-patterns
description: OutSystems UI numeric/status patterns — Badge, Counter, IconBadge, ProgressBar, ProgressCircle, Rating. Use when adding KPI cards, count badges, progress indicators, or star ratings.
---

# Numbers Patterns

> **Category:** Numbers — visual representation of counts, progress, and ratings.
> **Module:** OutSystemsUI

Patterns covered: `Badge`, `Counter`, `IconBadge`, `ProgressBar`, `ProgressCircle`, `Rating`.

## Requirement → block

| Requirement | Block |
|---|---|
| Inline numeric pill ("12 unread") | `Badge` |
| Icon with count overlay (bell + 5) | `IconBadge` |
| Dashboard KPI tile (number + label + icon) | `Counter` (often inside a `Card`) |
| Linear progress 0–100 | `ProgressBar` |
| Circular/radial progress 0–100 | `ProgressCircle` |
| Star rating display or input | `Rating` |

## Badge

Inline numeric pill — no placeholders, entirely argument-driven.

| Parameter | Type | Purpose |
|---|---|---|
| `Badge.Number` | Integer | The displayed count. |
| `Badge.Color` | `Entities.Color` | Background tint. |
| `Badge.IsLight` | Boolean | Lighter color variant. |
| `Badge.Shape` | `Entities.Shape` | `Sharp` · `SoftRounded` · `Rounded`. |
| `Badge.Size` | `Entities.Size` | `Small` · `Medium`. |
| `Badge.ExtendedClass` | Text | Extra CSS. |

Place inline next to text, inside table cells, or beside menu labels. For a labelled chip ("Active"), use [`Tag`](./content.md#tag) instead.

## IconBadge

Icon with an overlaid count badge (notification bell, message glyph).

| Parameter | Type | Purpose |
|---|---|---|
| `IconBadge.Number` | Integer | Count overlay. |
| `IconBadge.Color` | `Entities.Color` | Badge color. |
| `IconBadge.IsLight` | Boolean | Lighter variant. |

| Placeholder | Contents |
|---|---|
| `IconBadge.Icon` | A single Icon widget. |

## Counter

KPI card displaying a value, label, and icon.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Counter.BackgroundColor` | `Entities.Color` | — | Background fill. |
| `Counter.Height` | Integer | `150` | Height in pixels. |
| `Counter.IsVertical` | Boolean | `False` | Stack vertically (good for narrow columns / mobile). |
| `Counter.ExtendedClass` | Text | `""` | Extra CSS — use `"\"text-neutral-0\""` to invert text on dark backgrounds. |

**Counter has only ONE placeholder.**

| Placeholder | Contents |
|---|---|
| `Counter.Content` | All three zones: value (large), label, and icon — as separate child widgets in this single placeholder. |

There are **no** `Value` / `Label` / `Icon` parameters or sub-placeholders. Don't try to set them.

**Conventional widget order inside `Counter.Content`:**

```
Container (style="font-size-display") → Expression/TextWidget (the number)
Container → TextWidget (the label)
Container (right-aligned) → Icon
```

**Composition**

- Standard pattern: drop a `Counter` inside a `Card` for a dashboard tile, or inside `Columns3.Column1`/`2`/`3` for a row of three KPIs.
- For a row of dashboard counters, wrap in `Columns3` with `PhoneBehavior: Entities.BreakColumns.All` so they stack on mobile.


## ProgressBar

Linear progress indicator (0–100). No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `ProgressBar.Progress` | Integer | 0–100. Bind to an Integer attribute or LocalVariable. |
| `ProgressBar.ProgressColor` | `Entities.Color` | Fill color (e.g. `Entities.Color.Primary`). |
| `ProgressBar.TrailColor` | `Entities.Color` | Track color behind the fill (e.g. `Entities.Color.Neutral4`). |
| `ProgressBar.Thickness` | Text (CSS) | Bar height, e.g. `"\"8px\""`. |
| `ProgressBar.OptionalConfigs` | Record | `{ Shape: Entities.Shape.SoftRounded, … }`. |
| `ProgressBar.ExtendedClass` | Text | Extra CSS. |

## ProgressCircle

Circular/radial progress indicator (0–100). No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `ProgressCircle.Progress` | Integer | 0–100. |
| `ProgressCircle.ProgressColor` | `Entities.Color` | Stroke color (e.g. `Entities.Color.Success`). |
| `ProgressCircle.TrailColor` | `Entities.Color` | Track color behind the stroke. |
| `ProgressCircle.Size` | Text (CSS) | Diameter, e.g. `"\"120px\""`. |
| `ProgressCircle.Thickness` | Text (CSS) | Ring stroke width, e.g. `"\"8px\""`. |
| `ProgressCircle.OptionalConfigs` | Record | Misc. |
| `ProgressCircle.ExtendedClass` | Text | Extra CSS. |

**Bar vs Circle**

- `ProgressBar` for inline horizontal indicators (form completion, file upload).
- `ProgressCircle` for compact dashboard widgets (KPIs, donut-style displays).

## Rating

Star-based rating display or input. No placeholders.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Rating.RatingValue` | Integer or Decimal expression | — | Current value (0–`RatingScale`). Bind to an entity attribute or LocalVariable. |
| `Rating.RatingScale` | Integer | `5` | Maximum number of stars. |
| `Rating.IsEdit` | Boolean | `False` | `True` = interactive input, `False` = read-only display. |
| `Rating.Size` | `Entities.Size` | `Medium` | Star size. |
| `Rating.ExtendedClass` | Text | `""` | Extra CSS. |

**Event** `Rating.OnSelect` — payload `RatingValue` (Integer). Fires only when `IsEdit = True`. Pass with FULL PATH: `Parameter: "Rating.OnSelect.RatingValue"`.

## Cross-cutting rules

1. **`Counter` has one placeholder.** Don't try to use `Value`/`Label`/`Icon` placeholders — they don't exist.
2. **`ProgressBar`, `ProgressCircle`, `Rating` have no placeholders.** They're argument-only.
3. **Don't bind `Progress` to values outside 0–100.** Clamp upstream if needed.
4. **`Badge.Number` is Integer only.** For non-numeric labels ("Active", "Beta"), use `Tag`. As an alternative to the `Badge` block, you can compose a CSS-only badge from an `IContainer` with `badge` + `background-*` + `border-radius-circle` utility classes.

## Accessibility notes

- `Badge` and `IconBadge` should not be the *only* indicator of state. Always pair with text labels or `aria-label`.
- `ProgressBar` and `ProgressCircle` expose `role="progressbar"` with `aria-valuenow`/`aria-valuemin`/`aria-valuemax`. Don't override.
- `Rating` in edit mode is keyboard-navigable. Don't disable focus styling.
- `Counter` content should be readable by screen readers in label-then-value order. Place the `TextWidget` label before the value `Expression` if the visual order doesn't matter.
