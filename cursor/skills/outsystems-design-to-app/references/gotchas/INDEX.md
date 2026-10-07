# Gotchas — field-tested OutSystems UI traps

A collection of specific traps and anti-patterns that bite when generating OutSystems apps from design sources. Each entry: what goes wrong, why, how to detect, how to instruct Mentor to avoid it.

The **engine-level traps apply regardless of how the app is being built**.

**Why we have these:** field testing showed LLMs given a Figma routinely emit visually-plausible UI that ships broken — black SVGs on dark backgrounds, sections that vanish post-publish, tables that render "no records", primary buttons that double up. These gotchas are the catalog of those traps with the *why* attached.

---

## Theme + styling

| File | When it bites |
|---|---|
| [`theme-collisions.md`](theme-collisions.md) | OutSystemsUI theme rules collide with your CSS — sidebar pinned wrong, header doubled, links invisible. Seven reserved class names + the `!important` rule |

## Icons

| File | When it bites |
|---|---|
| [`svg-icon-baking.md`](svg-icon-baking.md) | Icons render black or blank on dark surfaces. Use the OS Icon widget with an explicit light color; never use `<i class="ph ph-X">` font-icon markup (doesn't render in ODC); inline SVG only if unavoidable, with an explicit `fill` |
| [`icon-coverage-checklist.md`](icon-coverage-checklist.md) | Per-build location checklist (sidebar nav, KPI corners, agenda markers, action chips, search shortcuts, buttons). Skipping any leaves the published surface feeling empty |
| [`icon-translation-figma.md`](icon-translation-figma.md) | Figma React sources commonly use Lucide; OutSystemsUI ships Phosphor. Translation table for the common ones |

## SPA structure / layout

| File | When it bites |
|---|---|
| [`spa-shell-fallback-fidelity.md`](spa-shell-fallback-fidelity.md) | Three fidelity details the runtime won't infer (they live in source JS), so state each explicitly in the anatomy: per-screen header title, source-matched table header, styled upload zone |
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
| [`publish-validator-rejections.md`](publish-validator-rejections.md) | A publish fails with an `OS-*` build-engine code (e.g. OS-APPS-40028) even after Mentor reports success. Read the publication's logs, report the code and cause, don't blindly re-publish; ask the user, then let Mentor fix the construct in one fix turn (Step 6b) |
| [`iterative-deployments.md`](iterative-deployments.md) | Keep updating the SAME ODC asset across iterations (same `app_key`, stable URL) instead of spawning `App_v1`, `App_v2`...; follow-up prompts describe only what changes |

---

## How to use this directory

These gotchas inform several stages of the design-to-app pipeline:

- **Step 2 (load OS UI knowledge):** Loaded on-demand alongside the `outsystems-ui/` and `screen-guides/` references when a design contains any of the matching patterns (SVG icons, theme overrides, tables with seed data, etc.).
- **Step 3 (compose `spec.json`):** The block-mapping pass and the per-screen `anatomy` should reference the relevant gotcha when its trap is detectable in the source (e.g., icons on dark containers → explicit light colour; figma React Lucide source → emit Phosphor names).
- **Step 5 (Mentor batches):** The one batch prompt's rules R1–R6 enforce the core gotchas (R1 theme-collisions, R2 svg-icon-baking, R3 tablerecords-seeding, R4 widget-link-slot, R5 duplicate-buttons, R6 spa-section-visibility).
- **Step 3d (acceptance checklist):** Acceptance-checklist items can reference gotchas as named verification points ("checked against `gotchas/svg-icon-baking.md`").

## Contributing

Each file covers, roughly in this order, the trap, why it happens, how to spot it in the source, and what the anatomy or spec states to avoid it, written as a rule (no internal links, app IDs, dates or names).
Keep it in our voice: we drive Mentor through `spec.json`; we don't mutate OML.
