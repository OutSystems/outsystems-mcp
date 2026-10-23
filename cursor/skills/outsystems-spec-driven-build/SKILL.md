---
name: outsystems-spec-driven-build
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a TEXT-ONLY structured spec. For Figma/image/HTML inputs, use `outsystems-design-to-app` instead. EXPERIMENTAL — Mentor is built for in-flow edits, so treat results as draft scaffolds for review, NOT ship-ready apps. A spec check first confirms every screen names a role the spec defines and that entities are listed, and warns when relationships or integrations are not stated; then it drives Mentor in two parts, data model then screens, each published, with guardrails against its known mistakes. Three entry modes — your own markdown spec file, an interview, or clone from an example template. Use when the user asks to "build a new app from spec", "generate an app from requirements", "have Mentor build [app] from this spec", "build an app from this written description", "write a spec for a new app and build it", or similar spec- or requirements-driven greenfield asks with NO design artifact. Not for OutSystems 11 (O11) or Service Studio.'
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

- Contents: `spec.md`, `answers.json` (interview mode), `result-data.json` and `result-screens.json` (plus one file per fix turn, such as `result-seed-fix.json`), `build-report.md`.
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

Ask each question in turn and wait for the answer (skip one the user already answered, such as new or existing). Write the answers to `<work>/answers.json` (one key per question `id`), then assemble the spec:

```bash
python3 "<skill>/scripts/build.py" assemble-spec --answers "<work>/answers.json" --app-name "<APP_NAME>" --output "<work>/spec.md"
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

Display the output. Ask the user a yes/no and wait for an explicit answer: *"Ready to fire Mentor with this spec?"* Name the target app in the question, using the Step 1 app name (a new Web app named X, created from the standard template in portfolio Y, or the existing app X) and say the build runs in two parts, the data model first and then the screens, each followed by a publish.

This go/no-go covers the Mentor edits only. **Each tenant write gets its own confirmation** (main `outsystems` skill): creating the app (Step 4) and each publish (Steps 5 and 6). Don't offer to approve those writes in advance.

> Use whatever confirmation affordance your harness provides (a question tool, or asking inline). The gate is the confirmation itself, not any particular tool.

### Step 4: Open the target app in one Mentor session

The live tool catalog decides which calls do each step; field names below follow the tool schemas. "The app name" below is the Step 1 app name.

- **Existing app** (an empty app the user created in ODC Studio and published once): search the tenant's apps by name and pick the result whose name is exactly the app name (ask the user if several match); its key is `app_key`. Open one Mentor session and pass `app_key` in the asset references of every Mentor prompt below.
- **New app.** First search the tenant's apps for one with that name: apps can't be deleted through this server, so a retry must not leave duplicates behind. The search only sees **published** apps, though: a new app shows up in the app listing, app info and the context lookups only after its first publish. So **never repeat a creation whose result you didn't see**; if the app key or session was lost before the first publish, ask the user to check ODC Studio before creating again.
  - **Creating an app is a tenant write: restate it ("create a new Web app named X in portfolio Y, from the standard template") and wait for explicit confirmation.** Then open one Mentor session and send the creation as a Mentor turn of its own, as the main `outsystems` skill describes: "Create a new Web application named X in portfolio Y from the standard Web application template. Do nothing else." Poll it to terminal and keep the new app's key from the run's per-app facts as `app_key`; pass it in the asset references of every Mentor prompt below.
  - **Portfolio:** use the portfolio the user names, or the one their existing apps belong to (the detailed app listing shows each app's portfolio key), and state it in the creation question and the creation prompt; never guess one. If Mentor refuses the creation, read the run's answer and supply what it asks for.
- **Fallback** when creation fails: ask the user to create the app in ODC Studio and publish it once there, then find it by name and use its key as `app_key`.

Use **this one session for both parts and their publishes** (main `outsystems` skill). Its idle limit applies while you wait on the user.

### Step 5: Part 1, the data model

The build follows the main `outsystems` skill's order: the data model is built and published first, so the screens are built on a saved revision and a failure in the screens part costs only that part.

```bash
python3 "<skill>/scripts/build.py" build-prompt --spec "<work>/spec.md" --part data
```

The output is the Mentor turn for part 1: the spec's data sections (overview, roles, data model, integrations, out of scope, acceptance criteria, notes) between `<spec>` and `</spec>`, then the data guardrails, among them:
- *"Build only the data part in this turn. Do NOT create screens, screen logic, navigation or menu entries yet."*
- *"Bootstrap the sample data with a Timer that runs when the app is published"*: a `Bootstrap<Entity>` action for each non-static entity that inserts only when the entity is empty, one generated `Create<Entity>` call per row, all called by `BootstrapData` from a Timer named `BootstrapTimer`; each action logs `inserted N rows` or `skipped, N present`; no SQL inserts, literal dates. Skipped when the spec says to skip sample data (Section 8 or 10).
- *"Do NOT publish the app in this turn."*

Send it as one Mentor turn on the session, unchanged: don't rewrite or drop the guardrails. Then:

1. **Poll the run to terminal** and read its completion signals for `app_key` **as the main `outsystems` skill describes**; save the terminal result to `<work>/result-data.json` (one replay of the run read from cursor 0, not the poll pages, so the summary isn't counted twice). Render the report, which records whether the turn landed:

   ```bash
   python3 "<skill>/scripts/build.py" render-report --spec "<work>/spec.md" --result "<work>/result-data.json" --label data --app-key "<app_key>" --output "<work>/build-report.md"
   ```

   It accepts a saved terminal response, the list of pages read from the start of the run, or either one as the harness saved it, and shows each turn's status, whether it **landed** (the main skill's completion signals: status, turn error, validation errors, whether the change was applied) and Mentor's summary. **Exit 1 means the last turn didn't land:** don't publish it as built.
2. **Check whether Mentor published on its own.** The prompt forbids it, but a build turn can still end in a publish. Look in the turn's result and events for a publication key or a "published" message. If it did, don't publish again: tell the user Mentor published without asking, and follow that publish to its outcome.
3. **If the turn didn't land**, send one targeted fix turn on the same session (the problems with concrete values, ending with "Do NOT publish the app in this turn"), save its result next to the first one, and render the report again with one `--result` and `--label` per turn, in order. A fix turn that landed clears the earlier failure. This is the part's one fix turn, a retry after a timeout included (below). **If the fix turn didn't land either, stop:** don't publish, and report the Landed lines and the `sessionId`.
4. **Publish part 1** (Publishing, below) once its last turn landed.
5. **Check the sample data** (skip when the spec says to skip it). `BootstrapTimer` runs right after the publish. Search the app's runtime logs for "Bootstrap", reading only lines written after this publish finished, and expect one line per non-static entity: `Bootstrap<Entity>: inserted N rows`, or `skipped, N present` when an earlier publish already seeded it. The timer runs asynchronously, so if nothing shows yet, wait briefly and check once more. If a line shows an error, or there is still nothing, don't start part 2:
   - Check with the actions context lookup whether `BootstrapData` exists. If it does, the fix is the wiring or the named action, not a new timer.
   - Send one fix turn on the same session that says what to fix and ends with *"Never create a second Bootstrap<Entity>, BootstrapData or BootstrapTimer. Do NOT publish the app in this turn."* Save its result as `<work>/result-seed-fix.json` and render the report again with it.
   - If it landed, confirm and publish it, and check again; if it didn't land, stop as in item 3. If the check still fails after that publish, carry on and say so in the report.

### Step 6: Part 2, the screens

Only after part 1 is published. If the user declined that publish, stop here unless they explicitly ask to go on; tell them everything stays unpublished in the session until the end.

```bash
python3 "<skill>/scripts/build.py" build-prompt --spec "<work>/spec.md" --part screens
```

The output is the Mentor turn for part 2: the whole spec, then the screen guardrails, among them:
- *"Respect the role-per-screen assignments in Section 4 EXACTLY. Do NOT default screens to anonymous/public access."*
- *"The data part already exists: build on it."* No new roles or entities, and no changes to the bootstrap actions or timer; a missing attribute or role is added and named in the summary.
- *"Do NOT publish the app in this turn."*

Send it on the **same session**, unchanged, and handle it as in part 1: poll, save the terminal result to `<work>/result-screens.json`, render the report with every build and fix turn so far, not the publish turns (`--result "<work>/result-data.json" --label data --result "<work>/result-screens.json" --label screens`, plus any fix turns, in order), check that Mentor didn't publish on its own, and send one fix turn if it didn't land; if that one didn't land either, stop as in Step 5, item 3. Then **publish part 2**.

> **Don't cancel a turn whose work you want:** its in-flight edits may not land. If a turn fails or times out, retry in the same session as the main `outsystems` skill describes: raise the turn-time ceiling where the catalog offers one; otherwise send a follow-up turn that asks Mentor to finish only what is still missing from this part, reusing what it already built. This retry is the part's one fix turn (Step 5, item 3). If the session ended after part 1 was published, open a new session on the same `app_key` and send part 2 there.

### Publishing (after each part)

Publishing is a tenant write. **Before each publish**, restate what will be published ("publish the data model of app X to its development environment", then "publish the screens of app X") and wait for explicit confirmation; ask as soon as the part has landed, since the session ends after the server's idle limit and takes everything unpublished with it. Then:

- **Publish with a publish turn**, as the main `outsystems` skill describes: a Mentor turn of its own on the session that asks Mentor to publish, with a short publish note in the prompt. There is no separate publish call.
- **Read the outcome from the finished run** (main `outsystems` skill): it succeeded, failed, timed out, or met someone else's newer revision.
- **If a publish turn fails, times out or reports no outcome**, follow the main `outsystems` skill: check it by its publication key, or else through the app's revision history, before you decide. Never publish again while the outcome is unknown. A failure that names a cause gets a further Mentor turn that fixes it, not an unchanged publish. A conflict goes to the user. If neither check settles it, ask the user to check ODC Studio before any new publish.
- **If the publish is refused**, handle it as the main `outsystems` skill describes: the remedy is a further Mentor turn that completes the work, not a retried publish.

If the user declines a publish, don't publish. Tell them the changes stay in the Mentor session (give the `sessionId`) and can still be published, but only until the session goes idle (main `outsystems` skill).

### Step 7: Check the build

When the part 2 publish has landed:

- Fetch the runtime URL from the environment's app info, as the main `outsystems` skill describes, and give the user the `url` as a link.
- **Access per screen:** compare each screen's roles with section 4, using the screens and roles context lookups for the app.
- Release the session once its work is published, as the main `outsystems` skill describes.

### Step 8: Report to the user (4–6 lines)

- App name, `app_key` and the revision of each publish, with the runtime URL as a link
- What was built (entity, role and screen counts) and anything Mentor skipped, added or left as a manual step
- The checks: sample data (Step 5), access per screen (Step 7), and anything still wrong
- **Sample data** (unless the spec skipped it): that the app now contains `BootstrapData` and `BootstrapTimer`, which runs on every publish, deployment and automatic patch in whichever stage the app is in and refills any empty sample-data table. To keep those tables empty, the timer has to be removed first: offer to do it in one Mentor turn on this app, confirmed and published like any other change
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
