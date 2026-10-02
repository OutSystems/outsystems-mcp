---
name: mobile-ui-design-tokens
description: Mobile UI design token taxonomy — color/spacing/typography/border/elevation values exposed as --token-* CSS variables. Use when theming a Mobile UI app, picking a token name for a spec, or referencing the three-tier (Primitives → Semantics → Component) hierarchy. Tokens are Mobile UI-only — OutSystems UI uses its own --color-*/--space-* variables (see styles-and-utilities.md).
---

# Design Tokens

Mobile UI Framework ships design tokens out of the box. **OutSystems UI (Reactive Web + Phone App Template) uses its own framework CSS variables instead** — see [`styles-and-utilities.md`](styles-and-utilities.md).

Tokens are named values for visual decisions. Apply via the matching utility class, or reference the CSS variable directly: `var(--token-<path>)` where `<path>` is the dotted token name with `.` replaced by `-` (e.g. `bg.primary.base.default` → `--token-bg-primary-base-default`). Color tokens also emit an `-rgb` sibling for `rgba()`.

## Three-tier hierarchy

```
Primitives  →  Semantics  →  Component tokens
```

| Tier | Purpose | Example | Override when |
|---|---|---|---|
| **Primitives** | Raw values | `primitives.blue.500: #2A5FE0` | Rebranding the entire palette |
| **Semantics** | Role aliases | `primary.500: {primitives.blue.500}` | Remapping "primary" without touching every usage |
| **Component tokens** | Specific UI roles | `bg.primary.base.default: {primary.500}` | Tweaking a specific surface in isolation |

**Use component tokens in CSS** — they're the most stable. Reach for primitives only when no semantic exists.

## Token catalog

### Spacing — `space.*` / `scale.*`

Scale: `space.0` (0) through `space.360` (360px). Common steps in pixel values: 0, 1, 2, 3, 4, 6, 8, 10, 12, 16 (= `base`), 20, 24, 28, 32, 36, 40, 44, 48, 56, 64, 72, 80, 96, 112, 128, 136, 144, 160, 200, 248, 296, 360.

**T-shirt aliases** (most common in utility classes): `xs` (4), `s` (8), `base` (16), `m` (24), `l` (32), `xl` (48), `xxl` (64).

`scale.*` mirrors `space.*` — same values, different name when used for sizing rather than spacing.

### Colors

**Primitives — `primitives.*`** — 16 color families, each with 12 shades (100–1200):
`neutral`, `base` (white/black), `red`, `pumpkin`, `orange`, `yellow`, `lime`, `green`, `teal`, `aqua`, `blue`, `indigo`, `violet`, `purple`, `magenta`, `pink`.
Path: `primitives.<color>.<NNN>` (e.g. `primitives.blue.500`).

**Semantic colors** — 5 role families, each mirroring a primitive with 12 shades:

| Semantic | Maps to | Use for |
|---|---|---|
| `primary.*` | `blue` | Brand-coloured surfaces, primary actions |
| `info.*` | `blue` | Informational alerts, helper banners |
| `success.*` | `green` | Success states, confirmations |
| `danger.*` | `red` | Errors, destructive actions, alerts |
| `warning.*` | `yellow` | Caution states, attention-needed banners |

**Component tokens — `bg.*` / `text.*` / `border.*` / `icon.*`** — the canonical "what to put where" tokens. Use these in CSS.

- **Backgrounds** (`bg.*`): `bg.primary.{base|subtle}.{default|press}` (plus `danger`/`success`/`info`/`warning`), `bg.neutral.{subtlest|subtle|base|bold|boldest}`, `bg.body`, `bg.surface.{default|inverse}`, `bg.input.{default|read-only|press|disabled|bold}`, `bg.select.{default|press}`, `bg.extended.<color>.{base|subtle}`.
- **Text** (`text.*`): `default`, `subtle`, `subtlest`, `primary`, `disabled`, `danger`, `info`, `warning`, `success`, `inverse`, `select`, `link.{default|press|visited}`, `text.extended.<color>`.
- **Border** (`border.*`): `default`, `boldest`, `subtle`, `subtlest`, `primary`, `success`, `warning`, `disabled`, `focus.{0|default|error}`, `danger.{base|press}`, `input.{default|press|read-only}`.
- **Icon** (`icon.*`): same role names as text (`default`, `primary`, `danger`, etc.).

### Typography — `display.*` / `heading.*` / `body.*` / `body.action.*` / `overline.*`

Composite tokens (font-size + weight + line-height + letter-spacing bundled together).

| Group | Sizes | Weights |
|---|---|---|
| `display.{sm,lg}` | 32px, 36px | light, regular |
| `heading.{h1…h6}` | 28 → 18px | regular, medium, semi-bold, bold |
| `body.{lg,md,sm}` | 16, 14, 12 | regular, medium, semi-bold, bold |
| `body.action.{lg,md,sm,xs}` | 20, 16, 14, 12 | medium (1% letter-spacing) |
| `overline` | 12 (uppercase) | regular, medium, semi-bold, bold |

### Border

- **Widths** — `border.border-size.{0|025|050|075}` → 0, 1, 2, 3 px.
- **Styles** — `none`, `solid`, `dashed`, `dotted`.
- **Radii** — `border.border-radius.{0|050|100|200|300|400|500|800|1000|full}` → 0, 2, 4, 8, 12, 16, 20, 32, 40, 999 px. `full` = pill/circle.

**Shape strategies** — three swappable border-radius systems at the theme level: `Soft` (subtle rounded 4–16px), `Round` (pill 999px small / 12–40px large), `Rectangular` (all 0).

### Elevation — `elevation.{1,2,3,4}`

| Token | Use for |
|---|---|
| `elevation.1` | Subtle (raised cards, hover states) |
| `elevation.2` | Standard (default card surface) |
| `elevation.3` | Prominent (popovers, dropdowns) |
| `elevation.4` | Deep (modals, sheets) |

Plus `backdrop` (70% opacity black) for modal scrim layers.

### Transitions

- **Curves** — `linear`, `quick` (`cubic-bezier(0,0,0.2,1)`), `base`, `expressive`, `bounce`.
- **Durations** — 0, 100, 150, 200, 300, 500, 1000, 1500 ms.

### Z-index

`bottom` (-99999), `0`, `100`–`500`, `top` (99999).

## Picking the right token

| You want to… | Use |
|---|---|
| Set the primary brand color | `var(--token-bg-primary-base-default)` / `var(--token-text-primary)` |
| Add standard padding to a Container | class `padding-base` or `var(--token-space-base)` |
| Make a card stand out | class `shadow-s` or `var(--token-elevation-1)` |
| Use the standard heading 2 style | class `heading2` |
| Use a danger/error red | `var(--token-text-danger)` / `var(--token-bg-danger-base-default)` |
| Match the input field's surface | `var(--token-bg-input-default)` |
| Pill-shaped button | `var(--token-border-radius-full)` |
| Modal backdrop | `var(--token-backdrop)` |

## Customizing tokens

Override any token's CSS variable on `:root` in the **Application Theme stylesheet**. For dark mode / theme variants, layer overrides under a class (`.theme-dark { … }`). Toggle the class on `<html>`/`<body>` from a client action.

See [`styles-and-utilities.md`](styles-and-utilities.md) for the broader CSS-customization rules.

## Anti-patterns

- ❌ Hardcoded hex / pixel values for color, spacing, typography, radius — overrides won't reach hardcoded values.
- ❌ Reaching for a primitive when a semantic exists — `var(--token-primitives-blue-500)` is brittle; `var(--token-bg-primary-base-default)` survives a rebrand.
- ❌ Picking arbitrary `space.*` values to hit pixel-perfect — round to the nearest scale step.
- ❌ Mixing tokens and OutSystems UI's framework variables in the same app — pick one (Mobile UI = `--token-*`; OutSystems UI = framework-defined `:root` variables).
- ❌ Overriding tokens at component / screen level when the change is brand-wide — override on `:root` in the Application Theme.
- ❌ Forgetting to update the `-rgb` sibling when overriding a color used in `rgba()` callsites — they drift silently.
