# Gotchas — field-tested OutSystems UI traps

A collection of specific traps and anti-patterns that bite when generating OutSystems apps from design sources. Each entry: what goes wrong, why, how to detect, how to instruct Mentor to avoid it.

**Sourced from `OutSystems/claude-oml-tool`'s [`validated/` corpus](https://github.com/OutSystems/claude-oml-tool/tree/main/oml-tool/skills/odc/validated)** — Hasan Derawan's team has been documenting these against real app builds (APPxxxx-cited evidence). Their build approach is different from ours (direct OML mutation via the Model API DLLs vs. our Mentor-driven flow), but the **engine-level traps they document apply regardless of how the app is being built**. Patterns and anti-patterns extracted here with attribution; verbatim C# / `plan.json` recipes intentionally omitted (those are OmlTool-specific).

**Why we have these:** field testing showed LLMs given a Figma routinely emit visually-plausible UI that ships broken — black SVGs on dark backgrounds, sections that vanish post-publish, tables that render "no records", primary buttons that double up. These gotchas are the catalog of those traps with the *why* attached.

---

## Theme + styling

| File | When it bites |
|---|---|
| [`theme-collisions.md`](theme-collisions.md) | OutSystemsUI theme rules collide with your CSS — sidebar pinned wrong, header doubled, links invisible. Five reserved class names + the `!important` rule |

## Icons

| File | When it bites |
|---|---|
| [`svg-icon-baking.md`](svg-icon-baking.md) | Icons render black or blank on dark surfaces. Use the OS Icon widget with an explicit light color; never use `<i class="ph ph-X">` font-icon markup (doesn't render in ODC); bake `fill="#fff"` into any inline SVG |
| [`icon-coverage-checklist.md`](icon-coverage-checklist.md) | Per-build location checklist (sidebar nav, KPI corners, agenda markers, action chips, search shortcuts, buttons). Skipping any leaves the published surface feeling empty |
| [`icon-translation-figma.md`](icon-translation-figma.md) | Figma React sources commonly use Lucide; OutSystemsUI ships Phosphor. Translation table for the common ones |

## SPA structure / layout

| File | When it bites |
|---|---|
| [`spa-shell-fallback-fidelity.md`](spa-shell-fallback-fidelity.md) | Four fidelity details the runtime won't infer (they live in source JS), so state each explicitly in the anatomy: per-screen header title, source-matched table header, styled upload zone, light icons on coloured tiles |
| [`spa-section-visibility.md`](spa-section-visibility.md) | HTML/SPA source hides sections with `display:none / .active` toggles; carry that CSS into the app and non-default screens render chrome-only. Don't put the toggle CSS in the anatomy |

## Widgets — anti-patterns

| File | When it bites |
|---|---|
| [`widget-link-slot.md`](widget-link-slot.md) | Nesting an interactive or data widget (Upload / Input / Form / Button / Table / Chart) inside a Link node makes the Link intercept clicks, so the file picker never opens and layout breaks |
| [`duplicate-buttons.md`](duplicate-buttons.md) | Two primary-action buttons for the same action on one screen (e.g. Sign In + Secure Login). Model each action once in the anatomy |
| [`tablerecords-seeding.md`](tablerecords-seeding.md) | A table bound to an unseeded source renders zero rows ("no records") even though the structure is correct. Seed via generated Create<Entity> actions |

## Publish + iteration

| File | When it bites |
|---|---|
| [`publish-validator-rejections.md`](publish-validator-rejections.md) | Constructs that pass the model API's `Save()` but fail ODC's stricter server-side publish validator (OS-APPS-40028). Round-tripping through Save/Load is NOT a sufficient quality bar |
| [`iterative-deployments.md`](iterative-deployments.md) | How to keep updating the SAME ODC asset across iterations (stable URL, revision counter) vs spawning a new asset every run. Relevant when chaining with `outsystems-change-planner` or running Mentor multiple times against the same shell |

---

## How to use this directory

These gotchas inform several stages of the design-to-app pipeline:

- **Step 2 (load OS UI knowledge):** Loaded on-demand alongside the `outsystems-ui/` and `screen-guides/` references when a design contains any of the matching patterns (SVG icons, theme overrides, tables with seed data, etc.).
- **Step 3 (compose `spec.json`):** The block-mapping pass and the per-screen `anatomy` should reference the relevant gotcha when its trap is detectable in the source (e.g., dark-container SVGs → flag for color baking; figma React Lucide source → emit Phosphor names).
- **Step 5 (Mentor batches):** The spec preamble can pull in selected gotchas as "constraint reminders" for Mentor.
- **Step 7 (build report):** Acceptance-checklist items can reference gotchas as named verification points ("checked against `gotchas/svg-icon-baking.md`").

## Contributing

When adding a new gotcha:

1. Each file has the same structure: **What goes wrong** → **Why (engine level)** → **How to detect** → **How to prevent** → **Attribution**.
2. Cite the source — either a `claude-oml-tool` `validated/` doc OR a field report (Slack / Issue / live build).
3. Anchor with an APPxxxx reference if you have one; that's the strongest evidence.
4. Keep it in our voice: we drive Mentor; we don't directly mutate OML. So talk about "tell Mentor to..." or "include in the spec.json".
