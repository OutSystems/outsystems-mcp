# How the Legacy Modernization toolkit works

> **Fallback snapshot.** The report is built from the installed plugin (see
> the skill's step 2). Use this file only for what the plugin doesn't carry,
> and for wording. Where it disagrees with the plugin, the plugin wins.

AI agents read a legacy application's source, build the new app on an
OutSystems Developer Cloud (ODC) tenant through Mentor, then test and fix it
until it passes. The user's team makes two decisions, validating the
requirements and picking the design, and reviews the result.

## The promise

- **High fidelity.** Every requirement comes from the code and cites the lines
  it came from, so the new app keeps the old rules.
- **Top-class UI.** A modern design the user chooses, built from standard
  OutSystems UI blocks and matched screen by screen.
- **High quality, proven.** 95% of requirements and 95% of the design, or the
  app goes back to the build, with a test for every requirement.
- **Minimal human intervention.** Agents build, test and fix on their own. The
  user validates the requirements, approves the design and reviews the result.

## When an app is done

An app is done when it meets **95% of its requirements** and matches **95% of
its approved design**. Anything short goes back to the build with the list of
what failed.

| | |
|---|---|
| Requirements gate | 95% functional coverage, scored against the extracted requirements, business rules and user journeys |
| Design gate | 95% of screens match the design the user picked; skipped, with the reason recorded, when there is no design artifact (no Figma and no mockups) |
| Fix rounds per gate | up to 5; each failure goes back to the build with what failed |
| Specialist roles | 6: planner, designer, developer, reviewer, tester, reporter |

If a gate still fails after its last round, the run finishes and the
Implementation Report records the gaps.

## The five stages

1. **Extract.** Reads the source and writes down what the app does: data,
   screens, rules and roles, each traced to its file. Output: the requirements
   collection and a Business Specification. Extraction and the build are
   separate commands, so the user checks the extracted requirements and
   corrects anything missing or wrong before starting the build.
2. **Design.** Draws design options for the new app's screens, in Figma or as
   HTML mockups. **The user picks the design**, and can ask for changes first.
   No screen is built before the pick, but the app, its data model and seed
   data can start while the user chooses. Output: the approved design the
   gates check against.
3. **Generate.** Builds on the tenant through Mentor, one small piece at a
   time. After each published piece the agent opens the app, checks it and
   fixes it before moving on. Output: a running app that grows step by step.
4. **Verify.** Drives the app in a browser against every requirement, then
   compares each screen with the design. Output: two scores against the 95%
   bar, with any remaining gaps listed.
5. **Hand over.** Writes the Implementation Report and packages every test run
   during the build into a toolkit the team can re-run. Output: the
   Implementation Report and the re-runnable test toolkit.

Each stage hands the next one a reviewable file, so a run can be stopped,
checked and resumed.

## The loops

- **Inner loop (every piece):** publish, test, fix, during Generate.
- **Outer loop (the gates):** below 95% on requirements or design, the
  failures go back to Generate and Verify runs again, up to 5 rounds. After
  that, what still fails is listed as a gap in the Implementation Report.
- **Back to design:** if Generate or Verify finds the design can't work as
  drawn (a missing screen, a rule it can't show), the designer extends or
  revises it in the style the user picked. The new screens pass the same
  reviewer and tester checks as the first ones; the workflow doesn't pause
  for a second pick.
- **Nothing is lost:** every check from both loops ends up in the test
  toolkit, so the team can re-run it after its own changes.

## What the user gets at the end

- A running app on their OutSystems tenant, built in small published steps
  they can open as it grows.
- A Business Specification of what the legacy app does, in business terms.
- An Implementation Report that traces each requirement to what was built.
- A test toolkit alongside the report: the same checks the agent ran while
  building the app, as automated browser tests the team can re-run, one per
  requirement, with traces and screenshots of each run.

## What it needs

- An OutSystems Developer Cloud tenant with Mentor available to the AI agent,
  reached through the OutSystems MCP server.
- Legacy extraction enabled on that tenant for the source language. Lotus
  Notes is on by default; other languages are enabled on request.
- A frontier AI model for generation. Smaller models finish too, with more
  cleanup.
- Optional: the Figma MCP for Figma designs (without it, designs are HTML/CSS
  mockups), and Playwright for drive-tests on a host with no browser of its own.

## Which legacy sources it reads

| Source | What the user hands over | Availability |
|---|---|---|
| Lotus Notes / Domino | a database export (.dxl) | on by default |
| COBOL | programs, copybooks, screen maps (BMS) and JCL | per tenant |
| Java, .NET, Node.js | the application's source tree | per tenant |
| AS/400 | DDS, RPG and CL source, or a CA 2E (Synon) model export | per tenant |
| AB Suite | the model export (.pmodel) | per tenant |
| Microsoft Access | the database file | per tenant |

## Which command

In Claude Code and Cursor, type the command. Codex and Kiro have no plugin
commands: ask the agent to follow the command's file in the plugin's
`commands` folder (for example "follow the workflow-legacy-app command file").
Either way, the agent runs that workflow with the skills below.

| Command | Job |
|---|---|
| `/extract-requirements` | Turn legacy source into requirements: publishes the requirements collection and the Business Specification, every item cited to its source lines. |
| `/generate-design-options` | Design the migration only: about three options, a pause for a pick, then the design gate on the picked option. Does not build or publish. |
| `/workflow-legacy-app` | Run a full migration: design options and the user's pick, the build on the tenant, both 95% gates with their fix rounds, then the Implementation Report and the re-runnable test toolkit. |
| `/outsystems-app-generation` | Build something new from a brief: one design, a build in small published steps, a test after each one. |
| `/create-or-update-skill-knowledge` | Keep what a project taught: turns the lessons from a finished run into proposed skill updates, for a person to review. |
| `/how-it-works` | This explanation, or the answer to one question about the toolkit. |

## Which skill

Each skill is a playbook the agent loads when the work calls for it,
including the traps that pass every visible check and still break.

| Stage | Skill | What it covers |
|---|---|---|
| Extract | `legacy-requirements-extraction` | legacy source into requirements and a Business Specification |
| Design | `figma-design-source` | colours, spacing and geometry from Figma |
| Design | `ui-exactness` | built screens measurably faithful to the design |
| Design | `outsystems-osui-idioms` | standard OutSystems UI blocks before custom styling |
| Build | `outsystems-app-build` | data, seed, screens, publish and verify |
| Build | `outsystems-app-generation` | a new app from a short brief |
| Build | `outsystems-ui-recipes` | sorting, paging, filters, wizards, languages |
| Build | `outsystems-agentic-app` | an in-app AI assistant on the app's own data |
| Fix | `outsystems-block-editing` | shared navigation, header and footer |
| Fix | `outsystems-css-theming` | why a style shows nothing, fixed at the cause |
| Fix | `outsystems-auth-and-deploy` | real sign-in and deploy failures with no visible cause |
| Prove | `outsystems-test-evidence-pack` | the re-runnable test toolkit: one browser test per requirement |
| Prove | `outsystems-handover-docs` | Business Specification and Implementation Report |

## Licence

Open source under the MIT licence:
<https://github.com/OutSystems/outsystems-mcp>.
