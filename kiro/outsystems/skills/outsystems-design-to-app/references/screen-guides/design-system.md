# Design System Setup Guide

## Creating a Proper App Theme

### Step 1: Discover Existing Themes

Before creating or modifying any theme, discover all themes in the app to see what exists. Then read the CSS details for each theme to inspect its StyleSheet and ThemeValues.

### Step 2: Set CSS Variables via ThemeValues

Use the theme's ThemeValues to override CSS variables — this is the correct way to brand an app. Common overrides:

| Variable | Purpose | Example |
|---|---|---|
| `color-primary` | Brand primary color | `#2563EB` |
| `color-secondary` | Secondary/accent color | `#1E293B` |
| `border-radius-soft` | Card/input corner radius | `8px` |
| `space-base` | Base spacing unit | `16px` |
| `font-base-size` | Base font size | `14px` |

### Step 3: Define Custom CSS Classes in Theme StyleSheet

For patterns not covered by utility classes, define custom CSS classes in the theme or screen StyleSheet. Always use CSS variables — never hardcode values:

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

### Step 4: Screen-Level vs Theme-Level StyleSheet

| When | Where to define CSS |
|---|---|
| Custom class used across multiple screens | Theme StyleSheet (shared, loaded once) |
| Custom class used on one screen only | Screen StyleSheet (scoped to that screen) |
| Custom class used inside one block only | Block StyleSheet (scoped to that block) |

### Anti-Patterns

| Wrong | Right | Why |
|---|---|---|
| `container.CustomStyle = "color: #1068eb"` | `container.Style = "\"text-primary\""` | Use utility class, not inline CSS |
| `widget.Style = "\"padding: 16px\""` | `widget.Style = "\"padding-base\""` | Padding is a utility class, not a raw CSS value in Style |
| Hardcoded hex in StyleSheet: `color: #1068eb` | `color: var(--color-primary)` | Theme changes propagate via variables |
| Same CSS class defined on 3 screens | Move to theme StyleSheet | DRY — define once, use everywhere |
| Inline width/height for layout | Use OutSystems UI columns + spacing classes | Responsive and consistent |
| `widget.CustomStyle = "margin-bottom: 16px"` | `widget.Style = "\"margin-bottom-base\""` | Spacing utilities are responsive and consistent |

### Style Property Escaping Reminder

Style and ExtendedClass are expression properties — string literals need escaped quotes in C#:

```csharp
// Correct — escaped quotes for the expression string
container.SetStyle("\"card shadow-s margin-bottom-base\"");

// Wrong — unescaped quotes, will cause runtime error
container.SetStyle("card shadow-s margin-bottom-base");
```
