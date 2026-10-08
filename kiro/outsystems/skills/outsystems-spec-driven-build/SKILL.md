---
name: outsystems-spec-driven-build
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a TEXT-ONLY structured spec — no design source needed. For Figma/image/HTML inputs, use `outsystems-design-to-app` instead. EXPERIMENTAL — Mentor is built for in-flow edits, so treat results as draft scaffolds for review, NOT ship-ready apps. A spec check first confirms every screen names a role the spec defines and that entities are listed, and warns when relationships or integrations are not stated; then it drives Mentor in one turn with guardrails against its known mistakes. Three entry modes — your own markdown spec file, an interview, or clone from an example template. Use when the user asks to "build a new app from spec", "generate an app from requirements", "have Mentor build [app] from this spec", "build an app from this written description", "write a spec for a new app and build it", or similar spec- or requirements-driven greenfield asks with NO design artifact.'
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Needs a shell with Python 3.8+ (standard library only; on Windows the interpreter may be `python` or `py -3`), so Claude Desktop's Chat tab, which has no shell, can't run it. Requires the `outsystems` MCP server connected and authenticated, with the session-based Mentor tools available, and builds on the main `outsystems` skill for session, polling and publish rules. Mentor must be enabled on the tenant.
metadata:
  version: "1.5.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Spec-Driven Build

Generate a new OutSystems app from a structured, text-only spec via ODC Mentor. The skill's job is **the prep step that makes Mentor succeed on the first try**: agree a complete spec with the user (roles, data model, screens and who can open each one, what is out of scope), check it, then send it to Mentor with guardrails against the mistakes Mentor commonly makes. Without that, it is just an unguided Mentor prompt.

**Load the main `outsystems` skill before Step 1: session, polling and publish rules come from it** (read the live tool catalog, one Mentor session per task, cursor polling and waiting from a fresh context where your harness offers one, the completion signals of a turn, confirm before every tenant write). This skill adds only what is specific to building from a spec; where the two seem to differ, the main skill wins.

## Prerequisites

- **The `outsystems` MCP server connected and authenticated**, per the main `outsystems` skill.
- **Mentor enabled on the tenant** (this skill drives Mentor).
- **A shell with Python 3.8+** to run `scripts/build.py` (standard library only). The script never calls the MCP; it handles the spec, the prompts and the report. The commands below say `python3`; on Windows use `python` or `py -3` if `python3` isn't found.
- **A target app.** Either a new Web app the skill creates (after confirmation) from the standard template, or an empty app the user already created in ODC Studio; see Step 4.

## When NOT to use

- **Adding features to an existing app** → drive Mentor directly with your prompt. Mentor preserves more context with an alive session.
- **Building from a design source** (Figma, screenshot, HTML mockup, front-end code) → use `outsystems-design-to-app`.
- **Building an app via free-form conversation** → drive Mentor directly with your prompt. This skill's value-add is only meaningful when there's a spec to be disciplined about.
- **Quick prototyping where you don't care about access rules or quality** → this skill's overhead doesn't pay off. A direct Mentor prompt is fine.

## Working folder

Keep the build's files in a `spec-driven-build/<APP_NAME>/` folder inside the user's current workspace (create it with the file-write tool), not directly in the home folder or a configuration folder. Below, `<work>` is that folder and `<skill>` is this skill's directory.

- Contents: `spec.md`, `answers.json` (interview mode), `mentor-result.json`, `build-report.md`.
- Retention: the user owns it; nothing expires.
- A Mentor run's terminal events can be large (50–500 KB). If a large result arrives inline, save it to `<work>` and re-read only what you need; if the harness already saved it to disk, pass that path on.

## Procedure

### Step 1: Get the spec

Ask the user for the **app name** and how they want to provide the spec. When the user has no spec file, **recommend the interview (Mode B)**, so the spec captures their own requirements. Offer the example (Mode C) only as a starting point to edit, never as the default, even when the request sounds like the example app.

Three entry modes:

#### Mode A: The user provides a spec file

Copy it to `<work>/spec.md`, then validate it (Step 2). If it's missing sections, either fix it with the user or fall through to Mode B's interview to fill the gaps.

#### Mode B: Interview the user

```bash
python3 "<skill>/scripts/build.py" list-questions
```

Ask each question in turn and wait for the answer. Write the answers to `<work>/answers.json` (one key per question `id`), then assemble the spec:

```bash
python3 "<skill>/scripts/build.py" assemble-spec --answers "<work>/answers.json" --output "<work>/spec.md"
```

#### Mode C: Start from the example

Copy `<skill>/templates/example-spec.md` to `<work>/spec.md` and fill it in with the user (the app name, the target app line, and every section). The blank template is `<skill>/templates/spec-template.md`.

### Step 2: Validate the spec

```bash
python3 "<skill>/scripts/build.py" validate-spec --spec "<work>/spec.md"
```

It reports **errors** (exit code 1) and **warnings** (exit code 0):

- **Errors:** a required section (1 Overview, 2 Roles, 3 Data model, 4 Screens + RBAC, 8 Out of scope) is missing, nearly empty, or still marked `(NOT PROVIDED`; a placeholder from `templates/spec-template.md` is left; no roles, no entities or no screens are listed; a screen has no role; a screen names a role that section 2 doesn't define (`Anonymous` and `All authenticated` are always allowed).
- **Warnings:** two or more entities and no relationships stated; section 6 Integrations missing or empty (it should say "None" when there are none); no `**Target app:**` line.

Fix every error with the user before going on. Show the warnings and let the user decide.

### Step 3: Confirm with the user before firing Mentor

Before firing Mentor, **show the user the final spec** and get explicit confirmation. Mentor calls can be expensive; a missed requirement at this step costs a full re-run.

```bash
python3 "<skill>/scripts/build.py" show-spec --spec "<work>/spec.md"
```

Display the output. Ask the user a yes/no and wait for an explicit answer: *"Ready to fire Mentor with this spec?"* Name the target app in the question: a new Web app named X, created from the standard template in portfolio Y, or the existing app X.

This go/no-go covers the Mentor edits only. **Each tenant write gets its own confirmation** (main `outsystems` skill): creating the app (Step 4) and the publish (Step 6). Don't offer to approve those writes in advance.

> Use whatever confirmation affordance your harness provides (a question tool, or asking inline). The gate is the confirmation itself, not any particular tool.

### Step 4: Open the target app in one Mentor session

The live tool catalog decides which calls do each step; field names below follow the tool schemas.

- **Existing app** (an empty app the user created in ODC Studio and published once): search the tenant's apps by name and pick the result whose name is exactly the app name (ask the user if several match); its key is `app_key`. Open one Mentor session and load the app into it.
- **New app.** First search the tenant's apps for one with that name: apps can't be deleted through this server, so a retry must not leave duplicates behind. The search only sees **published** apps, though: a new app shows up in the app listing, app info and the context lookups only after its first publish. So **never repeat a creation whose result you didn't see**; if the app key or session was lost before the first publish, ask the user to check ODC Studio before creating again.
  - **Creating an app is a tenant write: restate it ("create a new Web app named X in portfolio Y, from the standard template") and wait for explicit confirmation.** Then open one Mentor session and create the app in it from the standard Web application template, as the main `outsystems` skill describes, with the confirmed `name` and `portfolioKey`. Keep the new app's key as `app_key`.
  - **Portfolio:** use the portfolio the user names, or the one their existing apps belong to (the detailed app listing shows each app's portfolio key), and state it in the creation question; never guess one. If the create call is refused, read the error and supply what it asks for.
- **Fallback** when creation fails: ask the user to create the app in ODC Studio and publish it once there, then find it by name and load it.

Use **this one session for the build and the publish** (main `outsystems` skill). Its idle limit applies while you wait on the user.

### Step 5: Drive Mentor with the guardrails

```bash
python3 "<skill>/scripts/build.py" build-prompt --spec "<work>/spec.md"
```

The output is the Mentor turn: the whole spec between `<spec>` and `</spec>`, then the guardrails, among them:
- *"Respect the role-per-screen assignments in Section 4 EXACTLY. Do NOT default screens to anonymous/public access."*
- *"Bootstrap the sample data with a Timer that runs when the app is published"*: one `Bootstrap<Entity>` action per entity that inserts only when the entity is empty, one generated `Create<Entity>` call per row, all called by `BootstrapData`, which a Timer runs when the app is published; no SQL inserts, literal dates.
- *"Do NOT publish the app in this turn."*

Send it as **one Mentor turn** on the session, unchanged: don't rewrite or drop the guardrails, and don't split the spec over several turns.

> **Build order.** The main `outsystems` skill publishes the data model before asking for screens. This skill is an exception on purpose: the spec is agreed and validated up front (Steps 1–3), so Mentor builds the data model, the sample-data timer and the screens together in one turn, and the session is published once (Step 6). If the turn fails, retry it on the same session (below) before publishing anything.

Poll the run to terminal and read its completion signals **as the main `outsystems` skill describes**; save the terminal result to `<work>/mentor-result.json`. Then render the build report, which also records whether the turn landed:

```bash
python3 "<skill>/scripts/build.py" render-report --spec "<work>/spec.md" \
  --result "<work>/mentor-result.json" \
  --app-key "<app_key>" --output "<work>/build-report.md"
```

It accepts a saved terminal response or the list of pages read from the start of the run, and shows each turn's status, whether it **landed** (the main skill's completion signals: status, turn error, validation errors, whether the change was applied) and Mentor's summary. **Exit 1 means the last turn didn't land:** don't publish it as built. Each turn keeps its own Landed line, so a fix turn that landed clears an earlier failure.

**Check whether Mentor published on its own.** The prompt forbids it, but a build turn can still end in a publish. Look in the turn's result and events for a publication key or a "published" message. If it did publish, don't publish again: tell the user Mentor published without asking, follow that publication to terminal, and carry on from Step 7.

If the turn didn't land, send one targeted fix turn on the same session (the problems with concrete values, ending with "Do NOT publish the app in this turn"), save its result next to the first one, and render the report again with one `--result` per turn, in order.

> **Don't cancel a turn whose work you want:** its in-flight edits may not land. If a turn fails or times out, retry in the same session as the main `outsystems` skill describes (raise the turn-time ceiling where the catalog offers one, otherwise narrow the prompt).

### Step 6: Publish

Publishing is a tenant write. **Before publishing**, restate what will be published ("publish app X to its development environment") and wait for explicit confirmation. Then:

- **Publish the session** through the publish route the catalog offers (never by app key; main `outsystems` skill), with a short publish note.
- **If the publish is refused**, handle it as the main `outsystems` skill describes.
- **If the publish route itself is retired** (the call answers that it is no longer available and names another route, such as a Mentor turn whose message is "Publish"), that is not a refusal: use the route it names on the same session. It is the same publish, so the confirmation you already have covers it; poll that run to terminal.
- **Poll the publication to terminal**, as the main `outsystems` skill describes.

If the user declines a publish, don't publish. Tell them the changes stay in the Mentor session (give the `sessionId`) and can still be published, but only until the session goes idle (main `outsystems` skill).

### Step 7: Check the build

When the publish has landed:

- Fetch the runtime URL from the environment's app info, as the main `outsystems` skill describes, and give the user the `url` as a link.
- **Access per screen:** compare each screen's roles with section 4, using the screens and roles context lookups for the app.
- **Sample data:** the bootstrap timer runs right after the publish. Check the app's runtime logs (search for "Bootstrap") for the timer's "executed successfully" line, then spot-check that the screens show data; an error in the logs shows why a table stayed empty.
- Release the session once its work is published, as the main `outsystems` skill describes.

### Step 8: Report to the user (3–5 lines)

- App name, `app_key` and revision, with the runtime URL as a link
- What was built (entity, role and screen counts) and anything Mentor skipped or left as a manual step
- The Step 7 checks: access per screen, sample data, and anything still wrong
- The working folder and `build-report.md`
- If something is unpublished: the `sessionId`, and that it must be published before the session goes idle

## Anti-patterns: do NOT do these

The main `outsystems` skill's rules apply. Skill-specific:

- **Don't edit a System-module template app as the target.** `Template_*` / `template_*` / `OutSystems Sample Data` are rejected by Mentor's Model API. Create a new app from the standard template instead (Step 4).
- **Don't skip the spec validation step.** It catches screens without a role, roles the spec never defines and missing data model details before Mentor builds on them.
- **Don't omit the guardrails in the prompt.** They target Mentor's known mistakes; removing them brings those mistakes back.

## Related skills (chain after a successful build)

- `outsystems-app-architecture` — visualize what was built (it reads the published app).

Workflow: spec-driven-build (build and publish) → app-architecture (visualize).
