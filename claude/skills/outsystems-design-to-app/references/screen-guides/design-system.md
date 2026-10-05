# Design System Setup Guide

All theme customisation in this skill lives once in `design_system.theme_extensions` of `spec.json`: `:root` variable overrides plus any custom classes. There are no per-screen or per-block stylesheets.

## Step 1: Discover Existing Themes

Before changing anything, look at the app's existing theme to see which variables and classes it already defines.

## Step 2: Brand via `:root` variable overrides

Override OutSystems UI CSS variables in `:root` inside `design_system.theme_extensions` — this is the correct way to brand an app. Common overrides:

| Variable | Purpose | Example |
|---|---|---|
| `--color-primary` | Brand primary color | `#2563EB` |
| `--color-secondary` | Secondary/accent color | `#1E293B` |
| `--border-radius-soft` | Card/input corner radius | `8px` |
| `--space-base` | Base spacing unit | `16px` |
| `--font-size-base` | Base font size | `14px` |

## Step 3: Define custom classes in `theme_extensions`

For patterns not covered by utility classes, define custom classes in the same `theme_extensions` block. Always use CSS variables — never hardcode values:

```css
/* Good — uses CSS variables from the theme */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-xs) var(--space-s);
    border-radius: var(--border-radius-rounded);
    font-size: var(--font-size-xs);
    font-weight: var(--font-semi-bold);
}
.status-pill--active { background: var(--color-success); color: var(--color-neutral-0); }
.status-pill--pending { background: var(--color-warning); color: var(--color-neutral-10); }
.status-pill--closed { background: var(--color-neutral-4); color: var(--color-neutral-8); }

.kpi-card {
    padding: var(--space-m);
    border-radius: var(--border-radius-soft);
    background: var(--color-neutral-0);
    box-shadow: var(--shadow-s);
}
```

## Anti-Patterns

| Wrong | Right | Why |
|---|---|---|
| Inline style on a widget (`color: #1068eb`) | Utility class (`text-primary`) on the anatomy node | Use utility classes, not inline CSS |
| Raw padding/margin values on a widget | Spacing utilities (`padding-base`, `margin-bottom-base`) | Spacing utilities are responsive and consistent |
| Hardcoded hex in `theme_extensions`: `color: #1068eb` | `color: var(--color-primary)` | Theme changes propagate via variables |
| Same class defined in several places | Define it once in `theme_extensions` | DRY — define once, use everywhere |
| Inline width/height for layout | OutSystems UI columns + spacing classes | Responsive and consistent |
| Reserved class names (`sidebar`, `header`, …) | App-prefixed names | See [`../gotchas/theme-collisions.md`](../gotchas/theme-collisions.md) |
