# SPA section-visibility CSS carried from the source hides content

**The trap (HTML/SPA sources):** a single-page-app mockup keeps every section in one document, hides them with `display: none`, and a JS handler adds `.active` (CSS toggles it to `display: block`) on navigation. Looks right in the mockup. If you carry that visibility CSS into the app while splitting each section into its own screen, every non-default screen renders the chrome only and the content sits there invisible with `display: none` (the JS that would add `.active` never runs in ODC).

## Symptom

The published non-default screen shows the nav and header but an empty main content area. Inspect shows the content in the DOM at `display: none`.

## What this means for capture + the anatomy

When the source is an HTML/SPA doc and each section becomes its own screen:
- **Do NOT carry the section-toggle visibility CSS** (`.section { display:none } .section.active { display:block }`) into the anatomy or `design_system.theme_extensions`. The screen IS the section, so it should just render; no toggle is needed.
- If you did transcribe a wrapper class that has a `display:none` rule, drop the rule or the class from what you author.

**Exception, transient overlays.** Modals, dropdowns, popovers, success toasts, and mobile sidebars that slide in SHOULD stay hidden by default. For those, model the real OutSystemsUI widget (Modal / Popover / Sidebar / Toast) and wire the user action to its show/hide event, rather than a raw `display:none` + JS.

So the rule: strip the toggle CSS only when the section IS a screen's main content. Keep hidden-by-default for overlays, and realize them as OS widgets.

## How to detect during source inspection

```bash
grep -nE '\.(section|view|pane|screen)[^.]* *\{[^}]*display: *none' source.css
grep -nE '\.(section|view|pane|screen)[^.]*\.active *\{[^}]*display' source.css
grep -nE 'navigateTo|showSection|switchView|setActive|\.classList\.(add|remove)\(.active.' source.js
```

If sections are toggled by `.active` (not overlay open/close) AND each becomes its own screen, the pattern applies.

## How to prevent (what the anatomy states)

> *"The source uses a `display:none / .active → display:block` toggle to switch sections. Each section maps to its own screen, so its content renders directly; do NOT include the toggle CSS in theme_extensions. Keep hidden-by-default only for overlays (modals, toasts, popovers, mobile sidebars), modelled as OutSystemsUI widgets."*

## Field-test evidence

Bit three builds on 2026-06-02 (APP1388 prod, 6-screen ConstructionOperations, and a shadow build with the same source HTML).

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/spa-visibility-toggle-neutralization.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/spa-visibility-toggle-neutralization.md), validated 2026-06-02 (APP1388)

> Note: applies only when the SOURCE is an HTML/SPA doc. Reframed from `claude-oml-tool`'s chunk flow to "don't carry the toggle CSS into the anatomy."
