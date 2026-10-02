# Interactive widgets inside a Link get their clicks swallowed

**The trap:** if an interactive widget (Upload / Input / Dropdown / TextArea / Checkbox / Switch / Form / Button / RadioGroup) or a data widget (TableRecords / Chart / List) sits INSIDE a Link (a clickable/navigating node), the Link wraps it and intercepts interaction.

Consequences:
- The Link swallows clicks: a file picker never opens, an Input never focuses, a Button's OnClick doesn't fire (or fires the Link's navigation first).
- Table / chart layout breaks: the Link's `<a>` element does the wrong thing with the contained rows/headers and alignment goes off.

**Why it happens (engine level):** ODC renders a Link as an `<a>`, and an `<a>` wraps its children. Anything interactive inside it is inside an `<a>` at runtime, so the anchor's click handling and inline-layout win.

## What this means for the anatomy

- **Do NOT nest an interactive or data widget inside a Link/clickable node.** If a card or row needs to *contain* a Button, Input, Upload, Form, Table, or Chart, the card/row itself must NOT be the navigation target. Put the interactive widget as a normal child of a plain container, and give it its own `onClick`/action.
- **A Link (clickable card/row/tile) is fine ONLY when its content is static** and the whole thing is a navigation target, e.g. a summary card that drills into a detail screen with no interactive controls inside it.

Rule of thumb: if the node needs to receive direct user interaction (click, focus, type, drag, drop), it must not live inside a Link. If the node IS purely a navigation target with static content, a Link is correct.

## How to detect during source inspection

In the source HTML / Figma extract, watch for an anchor or clickable container wrapping something interactive (`<a class="…upload…" | …input… | …form…">`). When you author that region in the anatomy, split it: a clickable wrapper for navigation OR an interactive widget, not both nested.

## How to prevent (what the anatomy states)

> *"Upload section: outer container `doc-upload-zone` (dashed border, gradient icon, title, hint copy) with the Upload widget as a direct child. The container is NOT a Link; the Upload must receive clicks directly."*

## Field-test evidence

APP992 build `bld_fc70943003` (2026-06-03): an Upload nested inside a Link had every click swallowed and the native file picker never opened. Making the wrapper a plain container (not a Link) fixed it without losing the drop-zone styling.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/widget-grafted-into-link-slot.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/widget-grafted-into-link-slot.md), validated 2026-06-03 (APP992 bld_fc70943003)

> Note: sourced from `claude-oml-tool`'s HTML-graft flow (where the trap was an `<a>` slot wrapper). Reframed for the Mentor/anatomy flow as "don't nest an interactive/data widget inside a Link node."
