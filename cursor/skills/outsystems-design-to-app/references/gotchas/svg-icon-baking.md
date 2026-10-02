# Icons render black or blank

**The trap:** icons that look correct in the source (Figma / HTML) render BLACK on dark surfaces (sidebar nav, primary buttons, coloured tiles) or don't render at all in the published ODC app.

**Why it happens (engine level):**
1. **Font-icon markup does not render.** `<i class="ph ph-name">` (Phosphor) or `<i class="lucide ...">` markup works in a static mockup because the webfont is on the page, but ODC's SPA runtime doesn't load that font, so the glyph comes out blank.
2. **A raw inline `<svg>` gets baked to a background-image.** When an SVG ends up as a chunk, ODC bakes it into a base64 `background-image`. Once it's a background-image, `currentColor` resolves to BLACK (no DOM context to inherit from) and CSS rules like `.sidebar svg { fill: white }` can't reach it. So a `fill="currentColor"` icon on a dark sidebar becomes black-on-dark and is effectively invisible.

## What this means for the anatomy

Prefer the **real OutSystemsUI Icon widget** in the anatomy (`Icon="home"`, bare Phosphor name, not `ph-home` or `ph ph-home`). A real Icon widget renders via the theme font and inherits the container's text color, so it does not hit the baking problem. Two durable rules:

1. **Never put `<i class="ph …">` / `<i class="lucide …">` font-icon markup in the anatomy.** Use the OS Icon widget, or an inline `<svg>` if the glyph has no Phosphor match.
2. **On a dark/coloured surface, set the icon color explicitly.**
   - Real Icon widget: ensure the container node carries a light text color (e.g. `text-neutral-0`), since the Icon inherits it. Don't rely on a descendant `svg { fill }` rule.
   - Inline `<svg>` (only when no Phosphor match exists): bake the literal color onto the element, `fill="#fff"` (and `stroke="#fff"` for stroked icons). Inner shapes inherit, so one attribute on `<svg>` covers most icons. Never rely on `currentColor`.

In the anatomy, for any icon on a coloured/dark surface, spell out the color on the node:

> *"Sidebar nav icon: Icon `home` inside a node with `text-neutral-0` on the navy `#0a1a3d` sidebar (white, not currentColor). If a custom glyph is needed, inline `<svg fill="#ffffff" viewBox="...">`."*

## Anti-patterns

❌ An anatomy node that relies on *"icon inherits color from parent"* for an inline SVG (won't work once baked).
❌ A `.X svg { fill: ... }` rule in `design_system.theme_extensions` (won't apply to a baked SVG).
❌ Font-icon markup (`<i class="ph …">`) anywhere in the anatomy.
✅ The OS Icon widget with an explicit light text color on dark surfaces, or an inline `<svg>` with an explicit `fill`.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/currentcolor-svg-in-dark-container.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/currentcolor-svg-in-dark-container.md), validated 2026-06-03 (APP562, verified in live DOM)
- [`claude-oml-tool/oml-tool/skills/odc/validated/icons-render-verify.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/icons-render-verify.md), the source of the `<i class="ph">` doesn't-render rule

> Note: sourced from `claude-oml-tool`'s direct-OML/HTML-graft flow. Reframed here for the Mentor/anatomy flow; the font-icon and dark-surface-color rules are the parts that carry over.
