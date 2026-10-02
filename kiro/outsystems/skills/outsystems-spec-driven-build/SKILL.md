---
name: outsystems-spec-driven-build
description: '[Beta] Drive ODC Mentor to bootstrap an OutSystems app from a TEXT-ONLY structured spec — no design source needed. For Figma/image/HTML inputs, use `outsystems-design-to-app` instead. EXPERIMENTAL — Mentor is positioned for in-flow edits to existing apps; using it for end-to-end greenfield builds is a pattern this skill layers on top and quality varies with spec detail, so treat results as draft scaffolds for review, NOT ship-ready apps. Pre-flight validates the spec for things Mentor commonly fumbles (RBAC roles per screen, entity relationships, integration points), then drives Mentor with anti-failure guardrails. Three entry modes — your own markdown spec file, an interview, or clone from an example template. Use when the user asks to "build a new app from spec", "generate an app from requirements", "create a new app", "build app from scratch", "have Mentor build [app] from this spec", "build an app from this written description", or similar greenfield-build asks with NO design artifact.'
license: MIT
compatibility: Agent-neutral workflow for Codex and Claude Code (Claude Code is the most token-efficient path — see Harness notes). Requires Python 3.7+ (stdlib only) and the `outsystems` MCP server connected and authenticated, with the session-based Mentor tools available. Mentor must be enabled on the tenant.
allowed-tools: AskUserQuestion Bash Read Write Edit mcp__outsystems__auth_status mcp__outsystems__app_list mcp__outsystems__mentor_start_session mcp__outsystems__mentor_create_asset mcp__outsystems__mentor_load_asset mcp__outsystems__mentor_prompt mcp__outsystems__mentor_get_run mcp__outsystems__mentor_cancel_prompt mcp__outsystems__mentor_publish mcp__outsystems__publish_status mcp__outsystems__mentor_close_session
metadata:
  version: "1.3.1"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems Spec-Driven Build

Generate a new OutSystems app from a structured spec via ODC Mentor.
The skill's job is **the prep step that makes Mentor succeed on the
first try** — not "have Mentor build an app for me" (that's just an
unguided Mentor prompt).

**Why this exists:** field testing showed that under-specified Mentor
calls cost 5–10× more than tight ones. Peter R. spent $10 adding 7
form fields to an under-specified app. Vasco E.'s ambitious RFP spec
hit Mentor's known RBAC weakness in Claude. Donnie P. independently
demonstrated that disciplined upfront spec engineering keeps Mentor
builds clean — he used his own
[Spec-First TDD (SFTDD)](https://github.com/donnieprakoso/spec-first-tdd)
template to build
[`donnieprakoso/mcp-outsystems-docs`](https://github.com/donnieprakoso/mcp-outsystems-docs)
(an OutSystems docs MCP server, complementary to our catalog — see
README) and reports the discipline kept token cost predictable.

This skill's shape (interview → assemble → validate → fire) is **our
own** — designed for greenfield OutSystems-app builds in a single
Mentor invocation — distinct from SFTDD's iterative
Red → Green → Enhancement → Refactor cycle. But the underlying
conviction is the same: **agree on the spec before you fire the
expensive call.** That conviction is what Donnie's work surfaced as
real, field-tested signal; the OutSystems-specific guardrails below
are what we add on top.

## Prerequisites

Standard catalog prereqs — see CONVENTIONS §4b — **plus Mentor
enabled on the tenant.** Shared rules: §7b (API quirks), §8
(token-efficiency).

**One platform constraint to know:** Mentor works on an app loaded into
its session. This skill mints a fresh shell with `mentor_start_session`
→ `mentor_create_asset`, which needs a portfolio key (Step 1).

## When NOT to use

- **Adding features to an existing app** → use `outsystems-mentor-copilot`'s
  `add-feature` task. Mentor preserves more context with an alive session.
- **Building an app via free-form conversation** → drive Mentor directly
  with your prompt. This skill's value-add is only meaningful when there's
  a spec to be disciplined about.
- **Quick prototyping where you don't care about RBAC / quality** →
  this skill's overhead doesn't pay off. A direct Mentor prompt is fine.

## Procedure

### Step 1 — Identify or create the app shell

Mentor needs an app key to edit. Three paths in order of preference:

- **User has a fresh empty app already** → capture `APP_KEY` from
  their prompt or `mcp__outsystems__app_list` with their app name
  search.
- **Mint a shell programmatically (recommended)** →
  call `mcp__outsystems__mentor_start_session`, then
  `mcp__outsystems__mentor_create_asset` with `sessionId`,
  `name=<their-app-name>`, `assetType=WebApplication` (or `Agent`,
  matching the spec's intent) and `portfolioKey` (required;
  `app_list` with `detailed: true` shows the portfolio key of existing
  apps). By default the new app is cloned from the built-in template
  for its asset type. Use the new app's key as the `APP_KEY`.
- **User creates one in ODC Portal** → if they prefer the GUI path,
  ask them to create an empty app, then come back with the key.

**Do NOT use Template_* / template_* apps as the shell.** They are
System modules and Mentor's Model API refuses to load them with:
*"System modules cannot be loaded with the Model API. Consider using
the Clone method instead."* Use `mentor_start_session` →
`mentor_create_asset` (above) or have the user
clone via ODC Portal first. Confirmed via live test 2026-05-31 —
`Template Web App`, `Template_TestAgent`, `template_Agent`, and
`OutSystems Sample Data` all hit this error.

```
APP_KEY      = <asset key>
APP_NAME     = <human name>
CACHE        = ~/.claude/cache/outsystems-spec-driven-build/<APP_KEY>/
SKILL        = <this skill's directory>
mkdir -p "$CACHE"
```

### Step 2 — Get the spec

Three entry modes — pick based on what the user has:

#### Mode A: User provides a spec file

```bash
cp <user-provided-path>.md "$CACHE/spec.md"
python3 "$SKILL/scripts/build.py" validate-spec --spec "$CACHE/spec.md"
```

If validation fails (missing sections), the script prints what's
missing. Either retry with a corrected spec or fall through to
Mode B's interview to fill gaps.

#### Mode B: Interview the user

```bash
python3 "$SKILL/scripts/build.py" list-questions > "$CACHE/questions.json"
```

Then iterate through the questions, asking the user each one and
capturing each answer. After the interview, assemble the spec:

```bash
python3 "$SKILL/scripts/build.py" assemble-spec \
  --answers "$CACHE/answers.json" \
  --output  "$CACHE/spec.md"
```

#### Mode C: Clone from the example template

```bash
cp "$SKILL/templates/example-spec.md" "$CACHE/spec.md"
```

Then either edit-in-place or instruct the user to fill in the
placeholders. Validate before proceeding (Mode A).

### Step 3 — Confirm with the user

Before firing Mentor, **show the user the final spec** and get
explicit confirmation. Mentor calls are expensive ($1–$5 typical
for a greenfield build); a missed requirement at this step costs a
full re-run.

```bash
python3 "$SKILL/scripts/build.py" show-spec --spec "$CACHE/spec.md"
```

Display the output. Ask the user a yes/no and wait for an explicit answer:
*"Ready to fire Mentor with this spec? Estimated cost: $1–5."*

> Use whatever confirmation affordance your harness provides — Claude Code has
> a dedicated question tool, Codex asks inline. The gate is the confirmation
> itself, not any particular tool.

### Step 4 — Drive Mentor with anti-failure guardrails

Wrap the spec in a prompt that pre-empts Mentor's known fumbles:

```bash
PROMPT=$(python3 "$SKILL/scripts/build.py" build-prompt --spec "$CACHE/spec.md" --app-key "$APP_KEY")
```

The built prompt includes guardrails like:
- *"Respect the role-per-screen assignments exactly as specified.
  Do NOT default screens to anonymous/public access."* (Vasco's RBAC fix)
- *"Apply OutSystems UI to all screens. Do NOT generate bare HTML
  layouts."* (João's missing-UI fix)
- *"Use ODC terminology only. Do NOT reference 'Service Studio' or
  'eSpace' — those are O11 concepts."* (Inês's terminology fix)
- *"If you need to add a referenced library, ask the user to do it
  manually in Studio. Do NOT call `eSpace.AddDependency` — known
  broken."* (Peter's AddDependency NRE fix)

Then open a Mentor session on the shell and send the prompt. In the
current MCP that is `mentor_start_session` → `mentor_load_asset(assetKey=
"$APP_KEY")` → `mentor_prompt(message="$PROMPT")`; bind to whatever the
connected server exposes rather than hardcoding the sequence. Sending the
prompt returns a run handle — capture it for Step 5.

> Clone-from-example builds (Mode C) can instead let Mentor create the
> asset directly via `mentor_create_asset` with the example as its
> `templateAssetKey` — a natural fit for that mode.

### Step 5 — Wait for the run to finish

Poll the run to a terminal state (`succeeded` / `failed` / `cancelled`)
using the shared polling discipline — **don't re-implement it here.** The
mechanics (relaxed/drain cadence, cursor paging, sandbox-safe sleeps) live
in `outsystems-mentor-polling-behavior` and the run-status tool's own
schema; `outsystems-mentor-copilot` Step 4 states the same behaviour.

Same polling contract as `outsystems-mentor-copilot` SKILL.md Step 4 —
DO NOT re-implement here; the cursor rules and the Mentor sleep floor
below are identical to that skill's:

- The response is **terse by default** — `events: []`, `nextCursor: null` —
  while `status`, `currentStep` and `message` advance on their own. Pass
  `details: true` when you actually need event bodies; that is what populates
  `events` and `nextCursor`
- First poll: no `cursor`
- Subsequent polls: pass `nextCursor` from previous response
- If `nextCursor: null`, omit `cursor` on the next poll too
- Top-level `truncated: true` means the page was cut short — poll again
  immediately to drain it rather than sleeping
- Poll immediately while `nextCursor` keeps advancing — events are
  cursor-paged and batched, so drain polls are correctness, not waste.
  Once drained and still non-terminal, sleep the served `pollAfterMs`
  **and at least ~30 s** (upstream 0.16.0, verified 2026-08-26). Each poll
  costs a whole model turn, so the advertised interval is a floor to raise,
  never one to obey downward — a served 2 s figure is not one to chase.
  Re-read `pollAfterMs` from every poll; it changes. The ~30 s minimum is
  Mentor-only — `publish_status`, deploy and extlib polls follow their own
  description, ~15 s where it gives none (never slower than 15 s).
- Never bare-`sleep` a pause that long — harnesses block long standalone
  sleeps, and an `until …; do sleep 2; done` loop just moves the polling into
  Bash while holding the turn open. Use the harness's background-run mechanism
  and **end the turn**; pick the result up when it wakes you
- Expect 1 huge event early (Mentor's OML introspection) — 50–500 KB
- Expect the terminal poll to potentially exceed max tokens — on Claude Code
  the harness auto-saves oversized MCP results to disk and injects only the
  path (read the file back if so); a harness without that auto-save (Codex)
  gets the payload inline. See `## Harness notes`.
- Stop on `status: succeeded` / `failed` / `cancelled`. `running` and
  `cancelling` are both non-terminal — a `cancelling` run has not finished
  cancelling yet, so keep polling until it lands on `cancelled`
- **The completion flags are not a write signal.** `attemptedChange: true`
  and `changeApplied: true` came back on read-only question turns told to
  make no edits (tenant-measured 2026-08-26,
  `projects/portable-agent-skills/docs/adoption/deleterule-probe-verification.md`);
  re-running the same shape on 2026-08-27 returned `false` / `false`. They are
  inconsistent, and the failure mode that matters is the false positive — a
  turn that wrote nothing reporting `changeApplied: true`. `succeeded` is not
  proof either. Do not gate completion on any of them; check `validation`, and
  confirm any change you care about by reading the model back

### Step 6 — Save the terminal result

Same as `outsystems-mentor-copilot` Step 5 — three save paths:

1. **Terminal response inline + fits in context** → write it to
   `$CACHE/mentor-result.json`
2. **Auto-spilled to disk (Claude Code's >25 KB auto-save)** → `cp` to
   `$CACHE/mentor-result.json` OR pass path directly to Step 7. A harness
   without auto-save (Codex) gets the result inline — use path 1 or 3.
3. **Inline but you want it on disk** → write it

### Step 7 — Render the build report

```bash
python3 "$SKILL/scripts/build.py" render-report \
  --spec     "$CACHE/spec.md"             \
  --result   "$CACHE/mentor-result.json"  \
  --output   "$CACHE/build-report.md"     \
  --app-key  "$APP_KEY"                   \
  --run-id   "<runId>"
```

The report combines:
- The spec used
- Mentor's summary + any changes applied
- Counts (entities created, screens generated, actions added)
- Publish handoff (publish the Mentor session via the MCP's publish tool,
  **for human review — never auto-publish**)
- Suggested next steps (run `outsystems-mentor-copilot`'s
  `test-generation` task on the new actions, etc.)

**Publish outcomes** — the handoff is fired by a human, but the rules below
belong in the handoff text so whoever fires it reads them (upstream 0.16.0,
verified 2026-08-26):

- **A `mentor_publish` refusal is not a publish to retry.** When the server
  refuses the session, the refusal names the reason and the fix, and the
  remedy is a further Mentor turn that completes the work — never a second
  `mentor_publish`, which re-asks the same incomplete session and gets the
  same refusal. A `succeeded` run carrying `turn_error` is the usual cause:
  it is not a finished task, so the publish has nothing complete to take.
- **A publish with no observed outcome is not a failure to retry.** Poll
  `publish_status` with the returned `publicationKey` until `outcome` is
  `success` (`status: Finished`) or `failed` — the mentor-publish path
  reports `outcome`/`status`, not the gateway `state`. If a response ever
  carries `indeterminate: true` (the schema's Gateway-path flag), the server
  lost sight of the publish: it may still be building and may yet succeed.
  Re-poll `publish_status`, or verify with `env_app` — never re-publish. A
  second `mentor_publish` while the first is still running is what wedges
  the app. A `failed` outcome that is genuinely terminal: surface its code
  (`OS-BEW-*` / `OS-DPL-*` are retried server-side, so a returned code means
  the retries were exhausted) rather than re-publishing.
- **A rejection naming `tenant_not_allowed` is a per-tenant allowlist gate,
  not a lapsed sign-in.** The token is valid, so re-auth, re-registering and
  re-adding the server all fail identically while risking a working config.
  Confirm the configured host is the tenant meant (right account, wrong
  tenant returns this too); if it is right, stop and say the tenant needs
  enabling — retry once only if the user says it was.

### Step 8 — Report to user (3–5 lines)

- Output path
- App + revision
- Counts of generated artifacts
- Cost estimate (poll count × $0.10 rough)
- *"Open the build report. Run publish-handoff to commit, or run
  `outsystems-mentor-copilot` follow-up tasks (test-generation,
  add-feature) on the same Mentor session."*

## Cache rules

> The cache path stays at `~/.claude/cache/outsystems-spec-driven-build/<APP_KEY>/`
> on **every** harness — a shared cross-agent cache, not a Claude-only location.
> Codex reads and writes the same directory, so past spec + result pairs are
> visible regardless of which agent recorded the build.

- Location: `~/.claude/cache/outsystems-spec-driven-build/<APP_KEY>/`
- TTL: **none** — spec-driven builds are user-initiated, the user
  owns retention. Past spec + result pairs stay until cleaned up.
- Re-rendering a past run: just re-run Step 7. ~1K tokens.

## Token budget (estimate)

| Scenario | Mechanism | Total |
|---|---|---|
| Greenfield build, tight spec, simple app (5 entities, 8 screens) | spec + Mentor run + ~30 polls + report | **~30–60K** ($1–$2 on Opus 4.7) |
| Same but ambitious (15+ entities, RBAC, integrations) | spec + Mentor run + ~50–80 polls | **~60–120K** ($2–$5) |
| Re-running with same spec | Mentor session reuse + render | ~10K |
| Re-rendering a past build | Just render-report | ~1K |

Empirically: testers who used spec-driven patterns report 30–50%
lower token cost than ad-hoc conversational builds for similar app
complexity. The savings come from Mentor not spinning on
under-specified requirements.

## Harness notes

- **Claude Code** auto-saves any MCP result larger than ~25 KB to disk and
  injects only the file path into context, keeping the payload itself out of
  the model's context. This skill's Mentor polls routinely cross that
  threshold — Step 5 warns of one 50–500 KB OML-introspection event early, and
  the terminal poll can exceed the context limit outright.
- **Codex** has no such auto-save: the full MCP result is injected inline. So a
  greenfield build's Mentor polling costs materially more on Codex's first pass
  — every large `mentor_get_run` payload lands in context instead of spilling
  to disk. The token-budget table above reflects Claude Code; add the inline
  payload volume for a Codex estimate.
- On a harness without auto-save, follow Step 6 path 1 or 3 (write the result to
  `$CACHE/mentor-result.json` yourself) instead of relying on the harness spill
  in path 2.
- **Re-rendering a past build** (Step 7, `render-report`) makes zero MCP calls —
  it reads the local spec + result — so it costs the same (~1K tokens) on both
  harnesses. Re-running with the same spec reuses the Mentor session and also
  avoids re-fetching.

## Anti-patterns — do NOT do these

Shared rules apply (CONVENTIONS §8.4). Skill-specific:

- **Don't use a System-module template app as the shell** — they're
  rejected by Mentor's Model API with *"System modules cannot be
  loaded with the Model API. Consider using the Clone method instead."*
  Specifically avoid `Template_*`, `template_*`, `OutSystems Sample
  Data`. Use `mcp__outsystems__mentor_start_session` →
  `mcp__outsystems__mentor_create_asset` to mint a fresh shell, or
  have the user clone via ODC Portal.
- **Don't skip the spec validation step.** Validation catches missing
  RBAC, missing entity relationships, missing screen-role mappings
  before Mentor burns tokens on them.
- **Don't fire Mentor without user confirmation (Step 3).** A $1–5
  call shouldn't happen on assumption. Always show + confirm.
- **Don't ask Mentor to create a brand-new app shell in a prompt** —
  it edits the app loaded in its session. If the user has no shell,
  mint one with `mentor_start_session` → `mentor_create_asset`; the
  ODC Portal path is the fallback.
- **Don't auto-publish the result.** The build report ends with a
  publish handoff. A human reviews and publishes the session.
- **Don't omit the anti-Mentor-failure guardrails in the prompt
  (Step 4).** They were derived from real field-test failures —
  removing them re-introduces those failures.

## Related skills (chain after a successful build)

- `outsystems-mentor-copilot` (`test-generation`) — generate test
  scaffolds for the actions the build just created
- `outsystems-app-architecture` — visualize what was built
- `outsystems-app-documentation` — generate Markdown docs for the
  new app
- `outsystems-deploy-preview` — check the build before promoting to
  Test/Prod

Workflow: spec-driven-build → mentor-copilot test-generation →
app-architecture (visualize) → deploy-preview (gate to Test) →
publish.
