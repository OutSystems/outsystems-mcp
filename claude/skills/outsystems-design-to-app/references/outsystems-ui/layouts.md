---
name: osui-layouts
description: How to pick the right Layout block for a Reactive Web screen, and the placeholder structure each Layout exposes. Load this BEFORE building any screen — picking the wrong layout (especially defaulting to LayoutBlank) is the #1 source of fake-looking screens.
---

# OutSystems UI — Layouts

Every Reactive Web screen wraps in **exactly one Layout block** at the root. The Layout owns the chrome (sidebar, top bar, header, footer) and exposes named placeholders for content. **Pick the Layout first** — it dictates everything that comes after.

Layouts live in the **app's own `Layouts` flow** (not in the OutSystemsUI library).

## Picking a Layout

| Request says… | Layout | Why |
|---|---|---|
| "sidebar nav" / "side menu" / "left navigation panel" | `LayoutSideMenu` | Persistent left sidebar with `Navigation` placeholder + main content area. **Top bar is baked in** (don't add a second Layout). |
| Sidebar nav AND top header bar (banking apps, B2B dashboards, admin consoles, most authenticated SaaS) | `LayoutSideMenu` | Top bar is built in. Fill the `Header` placeholder for per-screen middle content. |
| "top nav" / horizontal menu with tabs across the top, NO left sidebar | `LayoutTopMenu` | Top bar with `Menu` block + 6-placeholder content tree. |
| Modal / popup with no chrome at all (login, embed, print stylesheet) | `LayoutBlank` | No menu, no chrome, just `MainContent`. |

**Don't default to `LayoutBlank` for full screens.** It gives nothing — no header, no nav, no chrome. Most user requests imply `LayoutSideMenu` or `LayoutTopMenu`. If the request mentions a left sidebar with nav items, use `LayoutSideMenu` (even if the design also has a top header bar — that comes for free).

**Exactly ONE Layout per screen — never nest.** Two Layout blocks at the screen root = duplicate placeholders, broken responsive grid, unfilled chrome, wireframe-sandwich rendering.

## ⚠️ MANDATORY: delete the default `LayoutTopMenu` before adding your chosen Layout

**`CreateScreen` always inserts a default `LayoutTopMenu` widget at the screen root.** If you skip this step and just add your chosen Layout, you end up with **two Layouts at the screen root** — the default `LayoutTopMenu` (still there with empty placeholders) AND your new one. The page renders both stacked.

Spec rule: **inspect, delete the default, then add the chosen Layout** — and add an acceptance-checklist item: *"Screen root has exactly one widget whose SourceBlock name starts with `Layout`."*

## Placeholder structure

### `LayoutSideMenu`

| Placeholder | Required content | Notes |
|---|---|---|
| `Navigation` | **`Menu` block instance** (from app's `Common` flow), with nav entries as `Link` widgets inside `Menu.PageLinks` | The left rail. **MUST** wrap a `Menu` block — never raw `Container` of nav items, never `AdvancedHtml Tag="nav"`. |
| `Header` | (often empty) | **Middle slot of the top bar only.** Brand and user widget are baked in (see anatomy below) — use this for per-screen content like a search box, breadcrumbs, or quick filters. |
| `Breadcrumbs` | (often empty or `Breadcrumbs` block) | |
| `Title` | `AdvancedHtml` `Tag: "h1"` with screen title | **MUST** go here — never inline in `MainContent`. |
| `Actions` | (often empty or primary action button) | Screen-level actions. |
| `MainContent` | Screen body | |
| `Footer` | (often empty) | |

**Top-bar anatomy** — three regions, only the middle one is per-screen:

```
┌──────────────────────┬─────────────────────────────┬──────────────────────┐
│  ApplicationTitle    │       Header  placeholder   │        UserInfo      │
│  (block in Common)   │       (per-screen content)  │  (block in Common)   │
└──────────────────────┴─────────────────────────────┴──────────────────────┘
```

- **Brand wordmark** → already exists as the `ApplicationTitle` block in `Common`, with an Expression bound to the app name. To restyle, edit `Common/ApplicationTitle` (add `ExtendedClass` + a theme CSS rule). **Don't hand-roll a wordmark** elsewhere.
- **Right side (user avatar, name, dropdown, AND chrome icons like notification bell, mailbox, theme toggle)** → owned by `Common/UserInfo`. Add chrome icons there, not in the `Header` placeholder.

### `LayoutTopMenu`

Six placeholders, in this order:

| Placeholder | Required content |
|---|---|
| `Header` | **`Menu` block** (REQUIRED — `Link` widgets in `Menu.PageLinks`) |
| `ActionButton` | header-level action button (often empty) |
| `Breadcrumbs` | breadcrumb trail (often empty) |
| `Title` | `AdvancedHtml` `Tag: "h1"` with screen title |
| `Actions` | screen-level action buttons (often empty) |
| `MainContent` | screen body |

Brand and user widget are baked into the Layout block's own widget tree — not placeholders. To change them, edit `LayoutTopMenu` in the app's `Layouts` flow.

### `LayoutBlank`

Single `MainContent` placeholder. **Truly no chrome** — no brand, no user widget, no top bar. Use ONLY for popup screens / modal content / explicit "no chrome" requests.

## Title placeholder — always `AdvancedHtml` h1

The screen title goes in the `Title` placeholder using `AdvancedHtml` with `Tag: "h1"` — never as plain text in `MainContent`. Preserves heading semantics for accessibility and theme styling.

## Anti-patterns

- ❌ **Nesting two Layout blocks** because the design has both a sidebar AND a top header bar — `LayoutSideMenu` already has a top bar.
- ❌ **Renaming the Layout instance to "Layout"** (or any generic name). Keep the SourceBlock name (`LayoutSideMenu`, `LayoutTopMenu`).
- ❌ **Putting a logo / brand image / user avatar inside the `Header` placeholder.** Edit `Common/ApplicationTitle` and `Common/UserInfo` instead.
- ❌ **Hand-rolling a brand wordmark as an `AdvancedHtml h1` + styled `TextWidget`** elsewhere in the screen. `Common/ApplicationTitle` already exists with the binding.
- ❌ **Putting the notification bell / mailbox icon / chrome icons in the `Header` placeholder.** They belong in `Common/UserInfo` (right side of top bar).
- ❌ **Defaulting to `LayoutBlank`** because the design "looks too custom." A bespoke visual treatment goes via theme variable overrides + `ExtendedClass`, not a custom layout shell.
- ❌ **Putting the screen title as plain text in `MainContent`.** Use the `Title` placeholder with `AdvancedHtml Tag="h1"`.
- ❌ **Skipping empty placeholders in `LayoutTopMenu`** — all 6 must be present in order.
- ❌ **Using `Container` to mimic a layout** (`Container > Container > Container` to fake the grid). Loses responsive behavior, theme integration, accessibility roles.
- ❌ **Putting raw `Link` widgets, `Container`s, or `AdvancedHtml Tag="nav"` directly in `Navigation` / `Header`.** These placeholders are for `Menu` block instances; nav links go inside `Menu.PageLinks`.
