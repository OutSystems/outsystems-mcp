# Design System Setup Guide

All theme customisation in this skill lives once in `design_system.theme_extensions` of `spec.json`: `css_variables` (`:root` variable overrides and new tokens) plus `classes` (`{ name, rule }` entries). There are no per-screen or per-block stylesheets.

## Existing app: read its theme first

When adding a screen to an existing app, read its theme with the theme context lookup (SKILL.md Step 1, "Adding a screen to an existing app") to see which variables and classes it already defines. The app's theme wins: add only new classes, prefixed with the new screen's name, and don't override existing OutSystems UI variables or `:root` values unless the user asks to restyle. A new app skips this.

## Brand a new app via `css_variables`

Override OutSystems UI CSS variables in `design_system.theme_extensions.css_variables` (emitted into the theme's `:root`) — this is the correct way to brand a new app. Common overrides:

| Variable | Purpose | Example |
|---|---|---|
| `--color-primary` | Brand primary color | `#2563EB` |
| `--color-secondary` | Secondary/accent color | `#1E293B` |
| `--border-radius-soft` | Card/input corner radius | `8px` |
| `--space-base` | Base spacing unit | `16px` |
| `--font-size-base` | Base font size | `14px` |

## Custom classes in `theme_extensions.classes`

For what utility classes and block inputs don't cover, define custom classes in the same `theme_extensions` block. A custom class is an add-on on a real block (via its `ExtendedClass`), never a replacement for the `Tag`, `Badge` or `Card` itself. Declare each value extracted from the design as a variable in `css_variables` and reference it with `var(--…)` in the rule, so `#EDF0ED` stays `#EDF0ED` but lives in one place:

```json
"theme_extensions": {
  "css_variables": {
    "--crm-status-active-bg": "#DCFCE7",
    "--crm-kpi-bg": "#EDF0ED",
    "--crm-kpi-radius": "12px"
  },
  "classes": [
    { "name": "crm-status-active", "rule": "background: var(--crm-status-active-bg);" },
    { "name": "crm-kpi-card", "rule": "background: var(--crm-kpi-bg); border-radius: var(--crm-kpi-radius);" }
  ]
}
```

Applied on the anatomy's real blocks (a node's `class=` is its `ExtendedClass`): `<Tag Color=Green Shape=Rounded class="crm-status-active">Active</Tag>` and `<Card class="crm-kpi-card padding-m shadow-s">`. The block supplies the chip or surface; the class carries only what the design adds, and spacing/shadow stay utilities.

## Anti-Patterns

| Wrong | Right | Why |
|---|---|---|
| Inline style on a widget (`color: #1068eb`) | Utility class (`text-primary`) on the anatomy node | Use utility classes, not inline CSS |
| Raw padding/margin values on a widget | Spacing utilities (`padding-base`, `margin-bottom-base`) | Spacing utilities are responsive and consistent |
| Hardcoded hex in a class rule: `color: #1068eb` | Reference a variable declared in `css_variables` (e.g. `color: var(--color-primary)`) | Theme changes propagate via variables |
| Same class defined in several places | Define it once in `theme_extensions` | DRY — define once, use everywhere |
| Inline width/height for layout | OutSystems UI columns + spacing classes | Responsive and consistent |
| A custom surface or chip class standing in for a block | `Card` / `Tag` / `Badge` with the class as `ExtendedClass` | The block carries structure and accessibility |
| Reserved class names (`sidebar`, `header`, …) | Prefixed names (app name on a new app, screen name on an existing app) | See [`../gotchas/theme-collisions.md`](../gotchas/theme-collisions.md) |
