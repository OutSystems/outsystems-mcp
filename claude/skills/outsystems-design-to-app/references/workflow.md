# Design-to-App Workflow

End-to-end pipeline for generating an OutSystems app from a design source via the OutSystems MCP / Mentor. Follows the flow described in `SKILL.md` — read it first for spec format rules, composition guidelines, and Mentor interaction patterns.

## Load References + Start Extraction (in parallel)

Launch ALL of these tool calls together in a single message:

```
Parallel group A (design extraction — start immediately):
  get_screenshot(nodeId)          # Figma
  get_variable_defs(nodeId)       # Figma
  get_design_context(nodeId)      # Figma
  # OR: Read the HTML/image file directly for non-Figma sources

Parallel group B (reference loading — runs at the same time):
  references/design-capture.md                          # Design Capture: author ANY source directly into styling-complete spec.json sections (Step 3.0) — load FIRST
  references/outsystems-ui/ui-reference.md              # OS UI widget reference (semantic hierarchy, anti-patterns, polish gates, Quick lookup)
  references/outsystems-ui/layouts.md              # Layout block + delete-default gate
  references/outsystems-ui/styles-and-utilities.md # utility classes + theme variables
  references/outsystems-ui/patterns/adaptive.md
  references/outsystems-ui/patterns/navigation.md
  references/outsystems-ui/patterns/content.md
  references/outsystems-ui/patterns/numbers.md
```

Load on demand (see SKILL.md for the mapping table):
```
references/outsystems-ui/charts.md      # when design has charts
references/outsystems-ui/maps.md        # when design has an interactive map
references/outsystems-ui/patterns/interaction.md   # Carousel, Sidebar, DatePicker, Dropdown
references/outsystems-ui/patterns/utilities.md     # AlignCenter, Separator, gestures
references/screen-guides/<screen-archetype>.md                   # dashboard | list-table | detail-view | edit-form | master-detail | gallery-grid | kanban | timeline | calendar | wizard | map-view | inbox-notifications | settings
references/screen-guides/design-system.md                        # theme tokens, brand recolor, palette swap (cross-cutting)
references/screen-guides/component-selection.md                  # picking the right block per requirement (cross-cutting)
references/screen-guides/states-and-feedback.md                  # empty/loading/error states, toasts (cross-cutting)
references/screen-guides/reusable-blocks.md                      # when to extract a Web Block vs inline (cross-cutting)
references/screen-guides/app-type-styling.md                     # styling defaults when the design is silent (cross-cutting)
```

## Input

Ask the user for:
1. **Design source** (required unless Pre-built spec provided) — Figma URL, web URL, image path, HTML file, or structured front-end code (TSX/React/HTML — highest fidelity)
2. **App context** (optional) — anything the user already knows about the existing app. For an existing app the skill gathers its screens / entities / theme itself with the context lookups (SKILL.md → "Adding a screen to an existing app"); reference existing elements by name, don't recreate.
3. **App name** (required) — target app name in the OutSystems environment. If the app doesn't exist, the skill creates it after confirmation (SKILL.md Step 1).
4. **Pre-built spec** (optional) — skip Stage 1, go straight to Stage 2.

## Design Extraction → author styling-complete `spec.json` sections

There is no separate capture file. Extract per source, then author the richness **directly into each screen's `anatomy`** (a widget-tree of real OS UI blocks with inline classes — see `references/design-capture.md`), plus the surrounding `design_system` / `entities` / `sample_data`. The anatomy carries: tree/nesting, per-node styling (real OS utility + custom classes), `bind`/`source` on data nodes, and explicit `series` on chart nodes. `spec.json` is the single artifact sent to Mentor.

**Code source — TSX / React / HTML (highest fidelity; recipe B):** Read the file. Transcribe, don't infer: imports/component names → block map; Tailwind/inline styles/constants → tokens; data hooks/actions/entity refs → data model; literal data arrays → sample data; source comments → block intent. This is the highest-fidelity input — a code source already states the tree, tokens, data model, and sample data.

**Figma** (Figma MCP `mcp__plugin_figma_figma__*`):
- Phase 1 calls launched above. If root `get_design_context` returns metadata XML, parse child node IDs and batch `get_design_context` on children (pairs of 2, skip failures).
- If `get_variable_defs` returns empty, extract colors from the design context code.
- Then author styling-complete `spec.json` sections (recipe A).

**HTML file**: Read the file, extract CSS (`:root` variables, class definitions) and structure (routes, components), then author styling-complete `spec.json` sections.

**Image**: Analyze visually. Hex values may need approximation — mark uncertain values as approximate. Author the screen `anatomy` (recipe A): walk the layout tree region by region, pick the real OS UI block for each node with inline classes read from the pixels, transcribe the visible sample data verbatim into `sample_data`, and infer the data model from columns/filters/chips.

## Stage 1: Compose spec.json

**If a pre-built spec is provided, skip to Stage 2** (after the Step 4 go/no-go).

Follow SKILL.md Step 3 in order (3.0 anatomy → 3.1 layout + skeleton → 3a block mapping → 3b the rest of the spec → 3c verify → 3d acceptance gates), using the extraction above. Save `spec.json` in the working folder; `assets/enriched-blueprint.json` is the schema.

## Stage 2: Invoke Mentor (MCP)

Follow SKILL.md Steps 4 to 6, which hold the batch prompt (the only prompt block), the confirmations and the publish; `mcp-flow.md` has the call sequence. Session, polling and publish rules come from the main `outsystems` skill. In short:

1. **Get the app into one session.** Existing app: `mentor_start_session` → `mentor_load_asset`. New app, only after the user confirms the creation: clone the tenant's "Template Web App" with `mentor_start_session` → `mentor_create_asset`, and keep that session. Fallback: the user creates the app in ODC Studio and you load it.
2. **Batch 1: entities + roles + seed**, as one `mentor_prompt` with the batch prompt prepended. Poll to terminal, read the completion signals, then **confirm and publish** so the data model is durable.
3. **Batch 2: screens + theme CSS + charts + chrome**, as another prompt on the same session (include the batch prompt's SHARED CHROME paragraph when `app_chrome.header.content[]` lists more than the brand and the avatar; do NOT split chrome into its own turn). Poll to terminal, **confirm and publish** again.

Use **2 batches** (field-tested: more turns means unacceptable latency; do NOT decompose section-by-section).

## Stage 3: Verify and report

- `env_app` for the runtime URL (the argument is `key`), `app_logs` (search "Seed") to confirm seeding ran, and the context lookups to spot-check screens and entities. The rendered app and the logs are the real check; Mentor's self-check is not.
- **Visual check and fix pass** (SKILL.md Step 6b): screenshot the live screen, compare with the design region by region, list the defects, and with the user's yes send one targeted fix turn (no publish in it), confirm, publish and re-check. At most two passes.
- Report to the user as SKILL.md Step 7 describes (including the Step 6b result).

## Follow-up

For refinements, send another `mentor_prompt` on the same open session. If the session has ended (idle limit, about 30 minutes), open a new session on the same `app_key`: it starts from the app as last published, so anything unpublished is gone.
