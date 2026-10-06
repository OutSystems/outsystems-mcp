---
name: outsystems-spec-driven-build
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a TEXT-ONLY structured spec — no design source needed. For Figma/image/HTML inputs, use `outsystems-design-to-app` instead. EXPERIMENTAL — Mentor is built for in-flow edits, so treat results as draft scaffolds for review, NOT ship-ready apps. A spec check first confirms every screen names a role the spec defines and that entities, relationships and integrations are stated; then it drives Mentor with guardrails against its known mistakes. Three entry modes — your own markdown spec file, an interview, or clone from an example template. Use when the user asks to "build a new app from spec", "generate an app from requirements", "create a new app", "build app from scratch", "have Mentor build [app] from this spec", "build an app from this written description", or similar greenfield-build asks with NO design artifact.'
license: MIT
compatibility: Agent-neutral workflow for Codex and Claude Code. Requires Python 3.8+ (standard library only) and the `outsystems` MCP server connected and authenticated, with the session-based Mentor tools available, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant.
metadata:
  version: "1.4.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Spec-Driven Build

Generate a new OutSystems app from a structured, text-only spec via ODC Mentor. The skill's job is **the prep step that makes Mentor succeed on the first try**: agree a complete spec with the user (roles, data model, screens and who can open each one, what is out of scope), check it, then send it to Mentor with guardrails against the mistakes Mentor commonly makes. Without that, it is just an unguided Mentor prompt.

**Session, polling and publish rules come from the main `outsystems` skill** (read `tools/list`, one Mentor session per task, cursor polling, the status watcher, confirm before every tenant write). This skill adds only what is specific to building from a spec; where the two seem to differ, the main skill wins.

## Prerequisites

- **The `outsystems` MCP server connected and authenticated**, per the main `outsystems` skill.
- **Mentor enabled on the tenant** (this skill drives Mentor).
- **Python 3.8+** to run `scripts/build.py` (standard library only). The script never calls the MCP; it handles the spec, the prompts and the report.
- **A target app.** Either a new app the skill creates (after confirmation) by cloning the tenant's own **"Template Web App"**, or an empty app the user already created in ODC Studio; see Step 4.

## When NOT to use

- **Adding features to an existing app** → drive Mentor directly with your prompt. Mentor preserves more context with an alive session.
- **Building from a design source** (Figma, screenshot, HTML mockup, front-end code) → use `outsystems-design-to-app`.
- **Building an app via free-form conversation** → drive Mentor directly with your prompt. This skill's value-add is only meaningful when there's a spec to be disciplined about.
- **Quick prototyping where you don't care about access rules or quality** → this skill's overhead doesn't pay off. A direct Mentor prompt is fine.

## Working folder

Keep the build's files in a `spec-driven-build/<APP_NAME>/` folder inside the user's current workspace (create it with the file-write tool), not in the home folder. Below, `WORK` is that folder and `SKILL` is this skill's directory.

- Contents: `spec.md`, `answers.json` (interview mode), `mentor-result.json`, `build-report.md`.
- Retention: the user owns it; nothing expires.
- Mentor's terminal `mentor_get_run` events can be large (50–500 KB). If a large result arrives inline, save it to `WORK` and re-read only what you need; if the harness already saved it to disk, pass that path on.

## Procedure

### Step 1: Get the spec

Ask the user for the **app name** and how they want to provide the spec. When the user has no spec file, **recommend the interview (Mode B)**, so the spec captures their own requirements. Offer the example (Mode C) only as a starting point to edit, never as the default, even when the request sounds like the example app.

Three entry modes:

#### Mode A: The user provides a spec file

Copy it to `WORK/spec.md`, then validate it (Step 2). If it's missing sections, either fix it with the user or fall through to Mode B's interview to fill the gaps.

#### Mode B: Interview the user

```bash
python3 "$SKILL/scripts/build.py" list-questions
```

Ask each question in turn and wait for the answer. Write the answers to `WORK/answers.json` (one key per question `id`), then assemble the spec:

```bash
python3 "$SKILL/scripts/build.py" assemble-spec --answers "$WORK/answers.json" --output "$WORK/spec.md"
```

#### Mode C: Start from the example

Copy `$SKILL/templates/example-spec.md` to `WORK/spec.md` and fill it in with the user (the app name, the target app line, and every section). The blank template is `$SKILL/templates/spec-template.md`.

### Step 2: Validate the spec

```bash
python3 "$SKILL/scripts/build.py" validate-spec --spec "$WORK/spec.md"
```

It reports **errors** (exit code 1) and **warnings** (exit code 0):

- **Errors:** a required section (1 Overview, 2 Roles, 3 Data model, 4 Screens + RBAC, 8 Out of scope) is missing or nearly empty; a placeholder is left (`<...>` or `(NOT PROVIDED`); no roles, no entities or no screens are listed; a screen has no role; a screen names a role that section 2 doesn't define (`Anonymous` and `All authenticated` are always allowed).
- **Warnings:** two or more entities and no relationships stated; section 6 Integrations missing or empty (it should say "None" when there are none); no `**Target app:**` line.

Fix every error with the user before going on. Show the warnings and let the user decide.

### Step 3: Confirm with the user before firing Mentor

Before firing Mentor, **show the user the final spec** and get explicit confirmation. Mentor calls can be expensive; a missed requirement at this step costs a full re-run.

```bash
python3 "$SKILL/scripts/build.py" show-spec --spec "$WORK/spec.md"
```

Display the output. Ask the user a yes/no and wait for an explicit answer: *"Ready to fire Mentor with this spec?"* Name the target app in the question: a new app named X (created from the tenant's "Template Web App"), or the existing app X.

This go/no-go covers the Mentor edits only. **Each tenant write gets its own confirmation:** creating the app (Step 4) and the publish (Step 8), as the main `outsystems` skill requires. Don't offer to approve those writes in advance. Editing in a Mentor session changes only the session's in-memory model, so the prompts themselves need no extra confirmation.

> Use whatever confirmation affordance your harness provides: Claude Code has a dedicated question tool, Codex asks inline. The gate is the confirmation itself, not any particular tool.

### Step 4: Open the target app in one Mentor session

Read the live `tools/list` first; argument names below are illustrative, the tool schemas are the source of truth.

- **Existing app** (an empty app the user created in ODC Studio): `app_list { search: "<app-name>" }` → its key is `app_key`. Then `mentor_start_session` → `mentor_load_asset`.
- **New app.** First check `app_list` for an app with the same name: **the MCP cannot delete apps**, so a retry must not leave duplicates behind. Then, **creating an app is a tenant write: restate it ("create a new Web app named X, cloned from your tenant's Template Web App") and wait for explicit confirmation.** Then:
  1. `app_list { search: "Template Web App", detailed: true }` → the tenant's own template. Its `assetKey` is the `templateAssetKey` and its `portfolioKey` is the portfolio for the new app. Do **not** fall back to the built-in default template: it pins outdated library versions and the first publish then fails.
  2. `mentor_start_session` → `mentor_create_asset { sessionId, assetType: "WebApplication", name, templateAssetKey, portfolioKey }`. **Pass `portfolioKey`:** the schema marks it optional, but the server rejects the call without it ("Portfolio ID is required"). Use the template's portfolio unless the user names another; never guess one. Capture the returned `applicationKey` as `app_key`.
  3. The new app appears in the catalog (`app_info`, `app_list`, the context lookups) **only after its first publish**. Until then, don't look it up there.
- **Fallback** when there is no "Template Web App" on the tenant, or creation fails: ask the user to create the app in ODC Studio, then find it with `app_list` and load it with `mentor_load_asset`.

Record the `sessionId` and use **this one session** for the build and the publish. A new session starts from the app as last published and carries none of the unpublished edits. The session ends after the server's idle limit (about 30 minutes) and takes unpublished edits with it.

### Step 5: Drive Mentor with the guardrails

Wrap the spec in a prompt that pre-empts Mentor's known mistakes:

```bash
PROMPT=$(python3 "$SKILL/scripts/build.py" build-prompt --spec "$WORK/spec.md")
```

The prompt ends with the guardrails, among them:
- *"Respect the role-per-screen assignments exactly as specified. Do NOT default screens to anonymous/public access."*
- *"Apply OutSystems UI to all screens. Do NOT generate bare HTML layouts."*
- *"Use ODC terminology only."*
- *"Do NOT publish the app in this turn."* Publishing is done separately, after the user confirms (Step 8).

Send it as one `mentor_prompt` on the session, unchanged: don't rewrite or drop the guardrails.

### Step 6: Wait for the run to finish

Poll the run to terminal **following the main `outsystems` skill** (cursor polling, the status watcher, wait only on statuses the live `mentor_get_run` schema lists). Don't re-implement the polling rules here.

Check `validation` (`errorCount`, `firstMessages`) on the terminal result; the `attemptedChange` / `changeApplied` flags are not a reliable write signal.

> **Don't cancel a turn whose work you want to keep.** A cancelled turn's edits don't land. Let a slow turn reach terminal; if it fails, retry in the **same session** with a narrower, more concrete prompt, as the main `outsystems` skill describes.

### Step 7: Save the result and render the build report

Save the terminal result to `WORK/mentor-result.json` (or, if the harness already saved it to disk, copy that file there). Then:

```bash
python3 "$SKILL/scripts/build.py" render-report \
  --spec       "$WORK/spec.md"             \
  --result     "$WORK/mentor-result.json"  \
  --output     "$WORK/build-report.md"     \
  --app-key    "<app_key>"                 \
  --run-id     "<runId>"
```

The report combines the spec used and Mentor's summary (what was created, what was skipped, any manual steps).

### Step 8: Publish

Publishing is a tenant write. Restate what will be published ("publish app X to its development environment") and wait for explicit confirmation. Then publish the **session** (never an app key) the way the live server accepts:

- **`mentor_publish { sessionId, comment }`**, then poll `publish_status` with the returned key to terminal, as the main `outsystems` skill describes.
- **If `mentor_publish` answers that it is deprecated** ("Use mentor_prompt with the message \"Publish\" instead"; `tools/list` may still advertise it), send **`mentor_prompt { sessionId, message: "Publish" }`** on the same session instead. It is the same publish, so the confirmation you already have covers it. Poll that run to terminal like any Mentor turn; it yields a publication key, so then poll `publish_status` with that key until `outcome` is terminal (`success`, with `status: Finished`).

Never re-publish on a refusal or an unobserved outcome: a refusal is answered by a further Mentor turn, and an unobserved outcome is re-polled or checked with `env_app`. When the publish has landed, fetch the runtime URL with `env_app`, as the main `outsystems` skill describes.

If the user declines, don't publish. Tell them the changes stay in the Mentor session (give the `sessionId`) and can still be published, but only until the session goes idle.

### Step 9: Report to the user (3–5 lines)

- Output path (the working folder and `build-report.md`)
- App + revision, and the runtime URL if published
- Counts of generated artifacts
- If not published: the `sessionId`, and that it must be published before the session goes idle

## Anti-patterns: do NOT do these

The main `outsystems` skill's rules apply. Skill-specific:

- **Don't edit a System-module template app as the target.** `Template_*` / `template_*` / `OutSystems Sample Data` are rejected by Mentor's Model API. Clone a new app from the tenant's "Template Web App" instead (Step 4).
- **Don't skip the spec validation step.** It catches screens without a role, roles the spec never defines and missing data model details before Mentor builds on them.
- **Don't fire Mentor without user confirmation (Step 3), and don't create an app or publish without confirming that specific write.**
- **Don't omit the guardrails in the prompt (Step 5).** They target Mentor's known mistakes; removing them brings those mistakes back.

## Related skills (chain after a successful build)

- `outsystems-app-architecture` — visualize what was built (it reads the published app).

Workflow: spec-driven-build → publish → app-architecture (visualize).
