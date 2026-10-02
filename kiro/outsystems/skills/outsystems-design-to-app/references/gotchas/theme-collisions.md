# Theme collisions with OutSystemsUI

**The trap:** Your screen CSS or chunk HTML uses class names / selectors that collide with rules already defined by OutSystemsUI's LayoutBlank theme. BOTH rules apply at runtime — yours and the theme's — producing doubled offsets, wrong positioning, sidebar pinned in the wrong place, links rendering invisible.

**Why it happens (engine level):** OutSystemsUI ships its own LayoutBlank theme with rules for common class names (`.main-content`, `.sidebar`, `.header`, `.content`, `.footer`) and elements (`a { color: inherit !important }`). When the source HTML / Figma extract reuses these names, both the theme's rule and the design's rule cascade. Specificity ties go to the theme.

## The five reserved class names

Never use these in chunk HTML or screen CSS without an explicit override:

| Name | What OutSystemsUI does with it | Symptom if you reuse it |
|---|---|---|
| `main-content` | Layout wrapper around the screen's MainContent placeholder | Doubled wrapper / wrong padding |
| `sidebar` | Position `fixed; right: 0` rule (right-side drawer) | Your left sidebar gets pinned to the right edge |
| `header` | Reserved layout slot | Header positioning conflicts |
| `content` | Generic content wrapper | Padding / overflow collisions |
| `footer` | Layout footer slot | Footer positioning conflicts |

**Fix paths:**
- **Preferred:** rename to an app-prefixed equivalent — `.app-sidebar`, `.dashboard-main-content`, `.banking-header`. The source's visual identity is preserved; the collision is gone.
- **Alternative:** add an explicit override block in the screen CSS that resets the theme's rule for your scope. More fragile.

## Other theme-collision anti-patterns

- ❌ **`<aside>` for a sidebar** — interacts with theme; use `<div class="app-sidebar">` instead.
- ❌ **`<table>` without explicit `display:table*` overrides** — `HtmlToWidgets` translates table tags to divs; without explicit rules, cells stack vertically.
- ❌ **`.sidebar nav a` selectors** — `<nav>` doesn't survive widget translation. Use `.sidebar a` and don't nest semantic elements inside the brand area.
- ❌ **Link colors without `!important`** — the theme's `a { color: inherit !important }` rule always wins otherwise. Sidebar nav links go invisible (parent text color = parent bg = invisible).
- ❌ **`ThemeGrid_*` utility classes outside `ThemeGrid_Container`** — the gutters break.
- ❌ **Authoring layout grid with `display: grid` + `Width*` props** — they don't compose; use `Columns2`-`Columns6` blocks.

## How to detect

In the source HTML or extracted CSS:
- Grep for any of the 5 reserved class names: `grep -E '\.(main-content|sidebar|header|content|footer)\b' source.css`
- Check for `<aside>`, `<nav>` inside any `.sidebar`, or raw `<table>` without overrides
- Look for link color rules without `!important`

In the `spec.json` block-mapping pass:
- If a section uses any of the reserved class names, flag and prepend `app-` to the spec.

## How to prevent (Mentor instructions)

In the Mentor prompt preamble for any design-to-app build, include this constraint:

> *"When generating screen CSS, NEVER use these class names: `main-content`, `sidebar`, `header`, `content`, `footer`. They collide with OutSystemsUI's LayoutBlank theme. Prefix with the app name (e.g., `banking-sidebar`). For sidebar / header / content / footer markup, use prefixed semantic divs (`<div class="app-sidebar">`) not raw `<aside>` / `<nav>` / `<header>` / `<footer>`. For link colors, use `!important` to override the theme's `a { color: inherit !important }` rule."*

In the `spec.json`'s `design_system.css_architecture` section, encode the rename rule:
- `"reserved_class_renames"`: `{ "main-content": "<app>-main-content", "sidebar": "<app>-sidebar", "header": "<app>-header", "content": "<app>-content", "footer": "<app>-footer" }`

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/v2-ui-theme-cookbook.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/v2-ui-theme-cookbook.md) — validated end-to-end through ODC publish 2026-05-09
- [`claude-oml-tool/oml-tool/skills/odc/validated/reserved-theme-class-names.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/reserved-theme-class-names.md) — validated 2026-06-02 (APP1388 cold-build sidebar overlap)
