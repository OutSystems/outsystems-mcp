# Theme collisions with OutSystemsUI

**The trap:** Your theme CSS or widget classes use class names / selectors that collide with rules already defined by OutSystemsUI's layout theme. BOTH rules apply at runtime — yours and the theme's — producing doubled offsets, wrong positioning, sidebar pinned in the wrong place, links rendering invisible.

**Why it happens (engine level):** OutSystemsUI ships its own layout rules for common class names (`.main-content`, `.sidebar`, `.header`, `.content`, `.footer`, `.main`, `.layout`) and elements (`a { color: inherit !important }`). When the source HTML / Figma extract reuses these names, both the theme's rule and the design's rule cascade. Specificity ties go to the theme.

## The seven reserved class names

Never use these on a widget or in `design_system.theme_extensions`:

| Name | What OutSystemsUI does with it | Symptom if you reuse it |
|---|---|---|
| `main-content` | Layout wrapper around the screen's MainContent placeholder | Doubled wrapper / wrong padding |
| `sidebar` | Position `fixed; right: 0` rule (right-side drawer) | Your left sidebar gets pinned to the right edge |
| `header` | Reserved layout slot | Header positioning conflicts |
| `content` | Generic content wrapper | Padding / overflow collisions |
| `footer` | Layout footer slot | Footer positioning conflicts |
| `main` | Layout main area | Doubled offsets / wrong height |
| `layout` | Root layout wrapper | Whole-page layout breaks |

**Fix:** rename with a prefix: on a new app, a short app-name prefix (`.banking-sidebar`, `.banking-header`); when adding a screen to an existing app, the new screen's name (`.orders-header`). The source's visual identity is preserved; the collision is gone.

## Other theme-collision anti-patterns

- ❌ **A hand-built sidebar/header container** — use the Layout's own placeholders instead: left navigation is `LayoutSideMenu`'s `Navigation` placeholder holding the `Menu` block; per-screen top-bar content goes in `Header`. (The `Sidebar` block is a slide-out panel, not navigation.)
- ❌ **Link colors without `!important`** — the theme's `a { color: inherit !important }` rule always wins otherwise. Sidebar nav links go invisible (parent text color = parent bg = invisible).
- ❌ **Authoring layout grid with `display: grid` + `Width*` props** — they don't compose; use `Columns2`-`Columns6` blocks.

## How to detect

In the source HTML or extracted CSS:
- Grep for any of the 7 reserved class names: `grep -E '\.(main-content|sidebar|header|content|footer|main|layout)\b' source.css`
- Look for link color rules without `!important`

In the `spec.json` block-mapping pass:
- If a section uses any of the reserved class names, prefix it (the app name on a new app, the new screen's name on an existing app) in the anatomy and `theme_extensions`.

## How to prevent

Enforced by batch-prompt rule R1 (SKILL.md Step 5).
