# Icons render black or blank

**The trap:** icons that look correct in the source (Figma / HTML) render BLACK on dark surfaces (sidebar nav, primary buttons, coloured tiles) or don't render at all in the published ODC app.

**Why it happens (engine level):**
1. **Font-icon markup does not render.** `<i class="ph ph-name">` (Phosphor) or `<i class="lucide ...">` markup works in a static mockup because the webfont is on the page, but ODC's SPA runtime doesn't load that font, so the glyph comes out blank.
2. **Inherited colour on inline SVG isn't reliable.** A `fill="currentColor"` SVG, or one coloured by a descendant rule like `.sidebar svg { fill: white }`, can come out black in the published app. On a dark sidebar that is black-on-dark, effectively invisible.

## The rule

1. **Prefer the real OutSystemsUI Icon widget** (`Icon="house"`, bare Phosphor name, not `ph-house` or `ph ph-house`). Never put `<i class="ph …">` / `<i class="lucide …">` font-icon markup in the anatomy.
2. **On a dark/coloured surface, set an explicit light colour** on the icon (e.g. `text-neutral-0`). Don't rely on a descendant `svg { fill }` rule.
3. **Inline `<svg>` only if unavoidable** (no Phosphor match): put the literal colour on the element, `fill="#fff"` (and `stroke="#fff"` for stroked icons). Never rely on `currentColor`.

In the anatomy, for any icon on a coloured/dark surface, spell out the colour on the node:

> *"Sidebar nav icon: Icon `house` with `text-neutral-0` on the navy `#0a1a3d` sidebar (white, not currentColor). If a custom glyph is needed, inline `<svg fill="#ffffff" viewBox="...">`."*

## Anti-patterns

❌ An inline SVG that relies on *"icon inherits color from parent"* (`currentColor`).
❌ A `.X svg { fill: ... }` rule in `design_system.theme_extensions`.
❌ Font-icon markup (`<i class="ph …">`) anywhere in the anatomy.
✅ The OS Icon widget with an explicit light colour on dark surfaces, or (only if unavoidable) an inline `<svg>` with an explicit `fill`.
