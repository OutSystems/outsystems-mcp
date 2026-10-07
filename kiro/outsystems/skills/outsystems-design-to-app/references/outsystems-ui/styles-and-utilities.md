---
name: osui-styles-and-utilities
description: Catalog of OutSystems UI design-system tokens, CSS variables, and utility classes — spacing, colors, typography, borders, shadows, button modifiers, layout/flex utilities, theming variables. Use to spec utility class names + CSS variable overrides in the design_system / anatomy of a Mentor spec.
---

# OutSystems UI — Styles & Utilities

Catalog of design-system tokens (CSS variables), utility classes, and theming rules. Spec authors reference these by name; Mentor handles the styling wiring.

## Naming convention

Every visual token has three forms: a **CSS variable** (`--<token>`), a **CSS class** (`.<token>`), and a **token name** in design files. Apply via `class=` on a widget (its Style Classes) or the block's `ExtendedClass`.

---

## Spacing

| Name | Value | Padding class | Margin class | CSS variable |
|---|---|---|---|---|
| `none` | 0 | `padding-none` | `margin-none` | `--space-none` |
| `xs` | 4px | `padding-xs` | `margin-xs` | `--space-xs` |
| `s` | 8px | `padding-s` | `margin-s` | `--space-s` |
| `base` | 16px | `padding-base` | `margin-base` | `--space-base` |
| `m` | 24px | `padding-m` | `margin-m` | `--space-m` |
| `l` | 32px | `padding-l` | `margin-l` | `--space-l` |
| `xl` | 40px | `padding-xl` | `margin-xl` | `--space-xl` |
| `xxl` | 48px | `padding-xxl` | `margin-xxl` | `--space-xxl` |

**Per-side:** `padding-{top|right|bottom|left}-{scale}` and `margin-{top|right|bottom|left}-{scale}`. **Axis shorthand:** `padding-{x|y}-{scale}` (x = left+right, y = top+bottom).

## Colors

Every color has three forms: `.background-<name>`, `.text-<name>`, `--color-<name>`.

**Brand:** `primary` (`#1068eb`), `secondary` (`#303d60`).
**Semantic** (each with Base + Light variant): `info`, `success`, `warning`, `error`.
**Neutrals:** `neutral-0` (white) → `neutral-10` (near-black) — 11 shades for surfaces / borders / text contrast.
**Color families** (each with `darkest`/`darker`/`dark`/base/`light`/`lighter`/`lightest` shades): `red`, `orange`, `yellow`, `lime`, `green`, `teal`, `cyan`, `blue`, `indigo`, `violet`, `grape`, `pink`.

**Prefer semantic names** (`primary`, `success`, `info`) over raw families (`blue`, `green`) — they survive a rebrand.

## Typography

| Heading class | Size-only class | CSS variable | Desktop / Tablet / Phone |
|---|---|---|---|
| — | `font-size-display` | `--font-size-display` | 36 / 34 / 32 px |
| `heading1` | `font-size-h1` | `--font-size-h1` | 32 / 30 / 28 px |
| `heading2` | `font-size-h2` | `--font-size-h2` | 28 / 26 / 24 px |
| `heading3` | `font-size-h3` | `--font-size-h3` | 26 / 24 / 22 px |
| `heading4` | `font-size-h4` | `--font-size-h4` | 22 / 21 / 20 px |
| `heading5` | `font-size-h5` | `--font-size-h5` | 20 / 19 / 18 px |
| `heading6` | `font-size-h6` | `--font-size-h6` | 18 / 17 / 16 px |
| — | `font-size-base` | `--font-size-base` | 16 (body) |
| — | `font-size-s` | `--font-size-s` | 14 (body small) |
| — | `font-size-xs` | `--font-size-xs` | 12 |
| — | `font-size-label` | `--font-size-label` | 11 |

**`.heading*`** = size + weight + spacing (use for actual headings). **`.font-size-h*`** = size only (use for non-heading large text like a KPI value).

**Weight:** `font-light` (300), `font-regular` (400), `font-semi-bold` (600), `font-bold` (700).

**Transform:** `text-lowercase`, `text-uppercase`, `text-capitalize`, `text-ellipsis`.

## Borders

**Radius:** `border-radius-none` (0), `border-radius-soft` (4px), `border-radius-rounded` (100px — pill), `border-radius-circle` (100% — full circle). Per-corner / per-side variants exist (`border-radius-top-soft`, `border-radius-bottom-right-none`, etc.).

⚠️ `border-radius-rounded` (pill) and `border-radius-circle` are for **chips / status pills / action buttons / avatars** — applying them to a content `Card` produces a warped "teardrop" shape.

**Border size:** `border-size-none`/`s` (1px)/`m` (2px)/`l` (3px).

## Shadows

| Class | CSS variable | Use for |
|---|---|---|
| `shadow-none` | `--shadow-none` | — |
| `shadow-xs` | `--shadow-xs` | Subtle elevation |
| `shadow-s` | `--shadow-s` | Cards |
| `shadow-m` | `--shadow-m` | Sticky headers |
| `shadow-l` | `--shadow-l` | Floating overlays / menus |
| `shadow-xl` | `--shadow-xl` | Modals |

## Buttons

⚠️ **`btn` is the load-bearing base class — never remove it.** Provides cursor, focus ring, padding, base typography, hover/active transitions, disabled-state styling. Modifiers (`btn-primary` / `btn-cancel` / etc.) layer on top.

**Types:** `btn`, `btn btn-primary`, `btn btn-cancel`, `btn btn-success`, `btn btn-error`.
**Sizes:** `btn-small`, default, `btn-large`.
**Shapes:** layer `border-radius-soft` (default) / `border-radius-rounded` (pill).
**Color overrides:** layer color utilities (`btn background-yellow text-neutral-0`).

## CSS custom properties (`:root`) — overridable in the theme

### App-level settings

| Variable | Default |
|---|---|
| `--header-color` | `#ffffff` |
| `--color-background-body` | `#f3f6f8` |
| `--color-background-login` | `#ffffff` |
| `--header-size` | `56px` |
| `--header-size-content` | `48px` |
| `--side-menu-size` | `300px` |
| `--bottom-bar-size` | `56px` |
| `--footer-height` | `0px` |

### Brand

| Variable | Default |
|---|---|
| `--color-primary` | `#1068eb` |
| `--color-secondary` | `#303d60` |
| `--color-primary-hover` | `#295fd6` |
| `--color-primary-selected` | `rgba(20, 110, 245, 0.12)` |
| `--color-focus-outer` | `#FFD337` |
| `--color-focus-inner` | `var(--color-neutral-10)` |

## Theming the app (dark mode, full rebrand, palette swap)

**The single most important rule:** put theme CSS on the **Theme's StyleSheet** (not a screen StyleSheet) and override the **existing OutSystems UI CSS variables** at `:root` (not invented variable names, not classes scoped to a wrapper).

OutSystems UI widgets read variables like `var(--color-neutral-0)` and `var(--color-background-body)` from their internal CSS — override at `:root` once and the entire app re-themes automatically.

### Canonical OS UI variables to override

| Variable | Override when |
|---|---|
| `--color-background-body` | Changing the page surface (mandatory for dark mode) |
| `--color-neutral-0` through `--color-neutral-10` | Inverting the contrast scale for dark mode |
| `--color-primary` / `-hover` / `-selected` | Brand recolor (set all three together) |
| `--color-secondary` | Secondary brand color |
| `--color-success` / `--color-warning` / `--color-error` / `--color-info` | Semantic color overrides |
| `--header-color` | Top bar color independent of page body |
| `--header-size` / `--side-menu-size` | Layout grid dimensions (rare) |
| `--color-focus-outer` / `--color-focus-inner` | Focus ring colors (must remain visible) |

### Dark mode template

```css
:root {
  /* Surfaces */
  --color-background-body: #0a0e1a;
  --header-color: #131829;
  --color-background-login: #0a0e1a;

  /* Neutrals — inverted scale */
  --color-neutral-0:  #131829;   /* surface */
  --color-neutral-1:  #1a2035;   /* subtle fill */
  --color-neutral-2:  #232944;   /* dividers */
  --color-neutral-3:  #2d3450;
  --color-neutral-4:  #3a4060;
  --color-neutral-5:  #4a5070;
  --color-neutral-6:  rgba(255, 255, 255, 0.35);
  --color-neutral-7:  rgba(255, 255, 255, 0.55);
  --color-neutral-8:  rgba(255, 255, 255, 0.75);
  --color-neutral-9:  rgba(255, 255, 255, 0.90);
  --color-neutral-10: #ffffff;

  /* Brand */
  --color-primary:          #6c5ce7;
  --color-primary-hover:    #7f70f0;
  --color-primary-selected: rgba(108, 92, 231, 0.18);

  /* Focus ring — keep visible on dark backgrounds */
  --color-focus-outer: #ffd337;
  --color-focus-inner: #131829;
}
```

### Theming anti-patterns

- ❌ **Inventing custom variable names** (`--bg-deep`, `--accent`). OS UI widgets read existing variables — custom names won't bridge.
- ❌ **Scoping theme CSS to a wrapper class** (`.banking-dark { … }`). Override `:root` directly; the cascade reaches everything.
- ❌ **Theme-wide CSS on a screen's StyleSheet** — only that one screen re-themes.
- ❌ **`!important` to override framework styles** — work with the cascade by overriding `:root` variables instead.
- ❌ **Hardcoding hex in widget Style** — breaks dark mode / theme variants. Use utility classes or variables.
- ❌ **Forgetting `--color-background-body`** when going dark — produces "floating dark cards on light page".

---

## Utility classes catalog

### Display

`display-block`, `display-none`, `display-inline`, `display-inline-block`, `display-inline-flex`, `display-flex`, `display-grid`, `display-contents`, `hidden`, `hide-on-service-studio`, `hide-scrollbar`.

### Position

`sticky`, `fixed`, `position-relative`, `position-absolute`.

**Absolute positioning helpers** (for elements with `position-absolute`):
`absolute-{top|right|bottom|left}`, `absolute-{top|bottom}-{left|right}`, `absolute-center`, `absolute-center-{top|right|bottom|left}`, `absolute-top-plus-header` (offset by `--header-size`).

### Width / Height

`full-width`, `full-width-vw`, `half-width`, `half-width-vw`, `full-height`, `full-height-vh`, `full-height-minus-header`, `half-height`, `half-height-vh`, `auto-height`, `tablet-full-width`, `phone-full-width`.

### Text

`text-align-{left|center|right}`, `wcag-hide-text` (visually hide but accessible), `white-space-nowrap`, `break-word`, `text-ellipsis`, `font-size-h1`–`h6` (size-only).

### Images

`img-cover`, `img-rounded`, `img-circle`, `thumbnail`.

### Flex layout

`display-flex` (on parent), plus alignment classes:
- `align-items-{baseline|center|flex-start|flex-end|initial|stretch}`
- `align-self-{flex-start|flex-end|center|stretch|baseline}`
- `align-content-{flex-start|flex-end|center|space-between|space-around|space-evenly|stretch|baseline}`
- `justify-content-{center|flex-start|flex-end|space-between|space-around|space-evenly}`
- `flex1` / `flex2` / `flex3` (flex-grow)
- `flex-direction-{row|row-reverse|column|column-reverse}`
- `flex-wrap` / `flex-wrap-reverse` / `flex-nowrap`

**Flex placement shortcuts** (combine align-items + justify-content):
`top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right`.

**Flex gap:** `gap-{xs|s|base|m|l|xl|xxl}`, `row-gap-{...}`, `column-gap-{...}`. Apply `gap-base` on a `display-flex` parent for consistent 16px spacing.

### Other utilities

| Class | Effect |
|---|---|
| `remove-card-gradient` | Strip default Card hover gradient |
| `separator` | Divider line styling (or use the `Separator` block) |
| `no-transition` / `no-transform` | Disable CSS transitions / transforms |
| `overflow-hidden` / `overflow-horizontal` / `overflow-vertical` | Overflow control |
| `table-responsive` / `table-no-responsive` | TableRecords horizontal-scroll on small screens |
| `is-horizontal` | Layout flag (RangeSlider etc.) |
| `list-item-no-click-effect` / `list-item-no-hover` | Strip ListItem interactive visuals |

## Anti-patterns

- ❌ Hardcoded hex codes in custom CSS — use variables (`var(--color-primary)`) so theme changes propagate.
- ❌ Inline `style="..."` on widgets — use class names (`class=` / `ExtendedClass`).
- ❌ Custom CSS rules duplicating utilities — before writing `.my-card { padding: 16px; box-shadow: …; }`, check if `padding-base shadow-s` does it.
- ❌ Using `--token-*` in OutSystems UI — that's Mobile UI. Use `--color-*`, `--space-*`, `--shadow-*`, `--border-radius-*`.
- ❌ Raw color families (`text-blue`) when a semantic name fits (`text-primary`) — semantics survive rebranding.
- ❌ `!important` to override framework styles — almost always means the override is at the wrong cascade level.

## Reference

- [OutSystems UI CheatSheet](https://outsystemsui.outsystems.com/OutSystemsUIWebsite/CheatSheet) — live source this doc tracks.
- [`./ui-reference.md`](./ui-reference.md) — OS UI widget reference (semantic hierarchy, anti-patterns, polish gates, Entities enums, Quick lookup).
