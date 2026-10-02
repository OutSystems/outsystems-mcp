# Four fidelity details the runtime won't infer

**The trap:** four specific patterns look right in the source but ship wrong, because the source encodes them in JavaScript that ODC's runtime doesn't execute. The build passes and the publish succeeds, but the rendered surface falls back to a static default that's wrong on every screen except the first. Mentor won't infer these, so the anatomy must state each one explicitly.

## Pattern 1 — Header/breadcrumb title stuck on the default

**Defect:** the header's current-page label (a breadcrumb "current" span, `#breadcrumb-current`, or the last span in a `.breadcrumb` box) shows the DEFAULT page's name on every screen, because the source updates it with JS at navigation time and the runtime runs no JS.

**Fix:** in each screen's anatomy, set the breadcrumb/title text to THIS screen's title literally. Source it (in order) from: a JS title map (`breadcrumbMap` / `pageTitles` / `titleMap`), the nav item that targets this screen, or the screen's own `<h1>`.

## Pattern 2 — Table header colour stuck on a default

**Defect:** a data grid header renders a fixed colour (often navy) regardless of the source. The real source header might be dark (solid brand colour) or light (a faint `rgba(...,0.05)` tint + bottom border).

**Fix:** in the anatomy, put the source's ACTUAL header background and text color on the table-header node's `class=`. A faint-alpha background is a deliberately LIGHT header; honour it, don't default to navy. **Contrast:** a light header needs dark text, a dark header needs white text. A faint-alpha bg reads as near-white over the grid, so it needs dark text even though the raw rgba has low luminance.

## Pattern 3 — Upload widget loses its styled drop-zone

**Defect:** a styled `.drop-zone` / `.upload-area` (dashed border, gradient icon, title, hint copy) collapses to a bare native Upload widget, losing the design.

**Fix:** in the anatomy, KEEP the styled container and its inner visual, and place the Upload widget as a child INSIDE it (not as a replacement). The Upload must be a direct child of a plain container, never inside a Link (see [`widget-link-slot.md`](widget-link-slot.md)).

## Pattern 4 — Icons on coloured tiles render BLACK

**Defect:** an icon inside a dark/gradient container (`.stat-icon`, a primary button, a coloured badge) renders black.

**Fix:** set the icon color explicitly on the node (light text color for a real Icon widget, or `fill="#fff"` on an inline `<svg>`). Same root cause as [`svg-icon-baking.md`](svg-icon-baking.md); cross-reference there.

## How to detect during source inspection

Before composing the anatomy, scan the source for: (1) a `.current` / `#breadcrumb` element updated by JS; (2) a `thead` / `.table-header` with a faint-alpha or non-default colour; (3) a styled `.drop-zone` / `.upload-area` vs a bare `<input type=file>`; (4) `<svg>` inside coloured containers with `.X svg { fill }` CSS. For each one found, state the explicit value in the anatomy.

## Why this is your job (not the theme's)

All four are cases of "the design is a contract" that the source expresses in JS/CSS the OML runtime doesn't execute. The value has to be baked into the anatomy at authoring time; Mentor handles the common shapes but not these novel ones.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/spa-shell-fidelity.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/spa-shell-fidelity.md)

> Note: reframed from `claude-oml-tool`'s chunk/plan flow to "state each detail explicitly in the anatomy." Applies mainly to HTML/Figma sources that encode these in JS/CSS.
