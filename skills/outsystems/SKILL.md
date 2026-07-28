---
name: outsystems
description: "OutSystems over MCP. Edit apps, publish, deploy, search tenant elements, manage external libraries. Use for ANY OutSystems task."
---

# OutSystems - Remote MCP

You are connected to OutSystems over the MCP HTTP transport. OutSystems is a cloud-native low-code platform where apps are built from OML (OutSystems Model Language), a binary format describing entities, screens, actions, and logic. Every tool call carries the harness's validated OAuth bearer; tenant + user identity are derived from the JWT, not from arguments.

**Once authenticated and the server's tools are visible**, read the live `tools/list` before your first non-auth OutSystems operation. This skill names domains, not tools — names, parameters, and defaults can change server-side, and the server is the source of truth. (Authenticating is the one exception: drive the auth flow first, as described below.)

## First use / setup

If the `outsystems` MCP tools aren't visible in your toolset, or a call returns `tenant not configured` / connection errors, the MCP server hasn't been registered against the user's tenant. Do this once per machine:

1. **Ask the user for their OutSystems tenant hostname.** Format: `<tenant>.outsystems.dev` (e.g. `mycompany.outsystems.dev`, `mytenant.outsystems.dev`). The tenant slug is whatever the user chose; do not assume a fixed `<short>-<region>-<index>` pattern. Prompt verbatim:
   > "Which OutSystems tenant should I connect to? It's the host portion of your OutSystems URL, typically something like `mycompany.outsystems.dev`."
2. **Normalize, then validate.** Accept whatever the user gives you (URL, hostname, hostname-with-path). Strip the scheme (`https://`, `http://`), any leading `www.`, trailing slash, and any path or query — keep only the host. The result must match `^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$`. Only ask again if the normalized value is still implausible (empty, contains whitespace, or clearly isn't a hostname).
3. **Construct the MCP URL**: `https://<TENANT>/mcp`.
4. **Register the server.** Run:
   ```
   claude mcp add -s user --transport http --client-id service_studio --callback-port 7890 outsystems <URL>
   ```
5. **Authenticate.** Proceed to the "Authenticating" section below. The agent drives auth via tool calls; the user does NOT click anything in `/mcp`.
6. **Retry the user's original request** once authentication completes.

If the user already has an `outsystems` MCP server registered but pointing at the wrong tenant, follow the same flow. The patches are idempotent for the same tenant and update the URL for a new one.

## Authenticating

OAuth-protected. The harness exposes two deferred tools; the agent drives the flow — the user does NOT run `/mcp -> outsystems -> Authenticate` manually.

- `mcp__outsystems__authenticate`: starts the OAuth flow; returns an authorization URL.
- `mcp__outsystems__complete_authentication { callback_url }`: finalizes auth for remote sessions.

**Lazy.** Before the first OutSystems tool call in a session, call `mcp__outsystems__authenticate` and share the returned URL with the user. Then:

- **Local session** (browser can reach `http://localhost:<port>/callback`): the server's real tools appear automatically — wait for the user's confirmation, then proceed.
- **Remote session** (callback page fails to load, e.g. SSH / devcontainer): have the user copy the full URL from their browser's address bar (`http://localhost:<port>/callback?code=...&state=...`) and call `mcp__outsystems__complete_authentication { callback_url: "<that URL>" }`.

**Reactive.** On `data.category: "AuthError"` mid-session (token expired, refresh denied, etc.): call `mcp__outsystems__authenticate` again, then retry the original call ONCE.

**Don't fall back to the `/mcp -> outsystems -> Authenticate` menu** — the deferred tool pair is always available; the menu is the host's emergency fallback.

**If `authenticate` itself errors** (server unreachable, DCR fails): surface the message verbatim and file against `OutSystems/outsystems-mcp`. Don't speculate about server internals.

## Tools at a glance

Discover the live catalog from the MCP server's `tools/list`; treat each tool's `description` + `inputSchema` as the source of truth. Don't rely on a hardcoded list — the set can change server-side. The tools group into these domains:

- **Apps** — list and inspect applications, their references, and revision history.
- **Context Service** — seven typed, read-only lookups over a tenant's elements (entities, actions, screens, structures, roles, themes, connections).
- **Mentor** — server-side OML editing as an async, multi-turn session.
- **Publish** — compile and publish edited OML to an environment.
- **Deployments** — promote builds across environments, roll back, run impact analyses.
- **External libraries** — upload, publish, inspect, and fetch source for .NET libraries.
- **Environments** — enumerate the tenant's environments.

### Caveats

Cross-tool behaviors not expressible in a single per-tool description:

- **Promoting a build needs an explicit source environment.** When you start a deployment with neither a `build_key` nor a `revision` pinned (and the operation isn't an undeploy), pass `from_env`; the target `env_key` is not used as the source on HTTP.
- **Publishing edited OML takes its app from the session, not arguments.** A publish derives `app_key` from the `mentor_session_token` claims; it needs `mentor_session_id`, `mentor_session_token`, and `env_key`. An explicit `app_key` is ignored.
- **Uploading an external library has a 50 MB decoded cap (~67 MB encoded `zip_b64`) and per-replica concurrency gating.** Pre-flight rejects oversize payloads; concurrent uploads queue per replica rather than reject.
- **The context lookups default `owned_only` to `true` when `app` is set, `false` tenant-wide.** Pass `owned_only: false` with `app` to keep rows inherited from referenced libraries (OutSystemsUI, Charts, etc.).

## Rules

- **Read `tools/list` before your first non-auth call.** This skill names domains; the server names tools. (Auth comes first; see Authenticating.)
- **Agent-facing tools.** Don't expose raw tool output; extract the relevant fields and present them naturally.
- **Go straight to the task.** No setup checks, no auth pre-flight beyond the lazy authentication step described above; identity comes from the harness-negotiated bearer.
- **Confirm before tenant-state mutations.** Before invoking any tool that can change tenant state, restate the planned change to the user and wait for explicit confirmation. Skip the prompt only when the user has already authorised this specific change in the current turn. A generic "go ahead with the task" earlier in the conversation is not authorisation for a specific destructive call. The destructive actions are: starting or rolling back a deployment, running a deployment-impact analysis, publishing OML, uploading/publishing/deleting an external library, and creating an app. Read-only and inert local-mutating tools are unaffected: listing or inspecting apps, the context lookups, any status/logs/messages poll, enumerating environments, and listing deployments. Editing in a mentor session changes only the in-memory mentor OML, not deployed tenant assets, so it does not require confirmation. The MCP host's own `destructiveHint` prompt is a backstop, not a substitute: this rule applies on every host regardless of whether the host gates on the hint.
- **OML stays server-side.** There is no download tool. Inspect an app through its references and the context lookups; edit it through the mentor flow (start a mentor run, then poll it until terminal). The OML lives in the server-side mentor session and never crosses the wire as bytes. When a user asks for the OML on disk, say plainly that the remote MCP transport does not expose a file-to-local-disk download (the server has no local filesystem to write to), and where useful offer the partially answerable portion (e.g. the app's revision history for the latest version number).
- **Never guess opaque IDs.** If `env_key`, `app_key`, an asset key, or a `mentor_session_*` token is missing and you can't resolve it, ask the user.
- **No selected environment.** Every environment-scoped tool takes `env_key` per call; the transport is stateless by design. When a user asks for a session-persistent `env select` style toggle, say so explicitly rather than refusing silently, and reframe the request so they pass `env_key` per call.
- **No local CWD.** The server has no view of the caller's filesystem. When a user asks about local paths, working directories, or CWD-relative artifacts, state the limit plainly and surface the closest server-side data inline (e.g. paste the environment-list payload back so the user can save it themselves) instead of attempting the operation. Don't silently route a write or a read through a non-MCP tool; the architectural fact has to reach the user.
- **Parallelize independent calls** (e.g. once you have an app key, fetch the app's info and the per-type context lookups concurrently).
- **Use `data.category`, not message text, for error retry decisions.** Categories: `AuthError`, `ValidationError`, `UpstreamError`, `InternalError`; upstream errors also carry `data.upstream_status`.
- **Long-running tools return an id; poll for status.** Applies to every deployment operation, publishing, all external-library operations, and mentor runs: the start call returns an id (a mentor run returns a `runId`), and you poll the matching status surface until it's terminal (a mentor run can also be cancelled). Per-tool polling shape is in each tool's live description.
- **Don't bare-sleep between polls.** Bare `sleep N` is blocked by many harnesses as a context-burning idle wait. Use your harness's background-task / background-sleep mechanism, **then end your turn**; the harness re-invokes you on completion. Calling the next tool right after a background sleep returns synchronously = no pacing. See "Pacing polls" under Mentor for cadence and the cursor pattern.

## Names

- `name` is the display form (may contain spaces, e.g. `"AI Agent Feedback Portal"`); `assetName` is the internal identifier (e.g. `"AIAgentFeedbackPortal"`). The `app:` parameter on the context lookups and app search accepts either — case-insensitive substring match against both the display name and its space-stripped variant.
- The canonical identifier is the **asset key** (UUID). Prefer it across calls; names can be edited, the key is stable.

## Answering

When you report on a tenant object that you looked up in this conversation — an application, environment, external library, deployment operation, the tenant binding itself — surface the canonical identifier alongside the human-readable name: asset key (UUID) for apps and external libraries, `env_key` for environments, operation key for deployments, tenant hostname for the tenant. The identifier is the stable reference the user needs to act on the result; names are ambiguous when two objects share one. This extends `## Names` (stable-key preference across calls) to the user-facing answer.

The rule fires when the agent did the lookup itself in this conversation **or** a follow-up action is plausible. Pure confirmation answers ("logged in", "yes that ran") can omit the identifier, and so can hand-back of an ID the user already typed.

## Mentor session round-trip

Mentor is a multi-turn conversation backed by a server-side session that holds the loaded OML. Driven via an async surface — start a run, poll its progress, cancel it if needed. Per-call args, response shape, polling cadence, cursor semantics, and error codes are in each tool's live `description` + `inputSchema`.

- **First turn** vs **resume turn** is determined by whether you pass a prior `mentor_session_token` when you start the run. The token is HMAC-signed and binds (tenant, user, session id, app, agent_resume_id); echo it back **verbatim** on resume.
- The newest `mentor_session_token` comes from the terminal payload — on **success** it's in `result` (alongside `mentor_session_id`, `summary`, and `events`); on a **failed/cancelled** run the terminal `error` object carries the same `mentor_session_id` + a freshly minted `mentor_session_token`. A failed/cancelled turn never advances committed state, so **resume the same session** with those (retry the prompt / continue) instead of starting a fresh `app_key` session, which burns a per-tenant slot and drops unpublished edits. Use the newest token on the next start. Exception: when the failed run's error `code` is `session_not_found` (the session is gone) — and on first-turn (`app_key`) init failures, where the error is bare and carries no credentials — start a fresh `app_key` session instead.
- Sessions auto-GC after 30 min idle. Resuming after GC transparently re-downloads the OML; same `mentor_session_id` and conversation continue.
- To publish the edited OML you need `mentor_session_id` + `mentor_session_token` from the most recent terminal-success run result.

**Pacing polls:**

- Poll the run **immediately** after starting it, and again immediately while the cursor advances — mentor events are cursor-paged and arrive in batches.
- Pause only when the cursor is drained and `status` isn't terminal. **~30s is a reference for mentor**, not a target — without one, agents tend to drift to 60–180s. Publish, deployment, and external-library status polls finish faster; **5–15s** is fine for those.

**When to use the mentor flow vs the context lookups:**
- For *info* about an app, prefer the context lookups. Lightweight, structured, no OML download. Only fall back to mentor when context can't answer (deep OML internals, logic flow traversal).
- For *edits*, the mentor flow is the only path.
- Reuse the same session across follow-up turns in one task; the server-side OML and tool history stay loaded.
- **Resume with `fresh_context: true`** (a resume-only flag on the mentor start call — pass it alongside `mentor_session_id` + `mentor_session_token`) when the conversation hits its max length (`OS-AISA-40001`), mentor starts hallucinating entities/actions that don't exist, or you switch to another task on the *same* app. It starts a new conversation over the session's *current* (already-edited) OML while keeping the session slot, the server-side OML, and any unpublished edits — so it doesn't burn a second per-tenant session slot and doesn't discard in-session work. It's a boolean and strictly typed: pass JSON `true`, not the string `"true"` or `1`. On the first turn (`app_key`, no token) it's ignored. If the server predates the flag it rejects the whole call (unknown property), so only send it when recovering. On an `OS-AISA-40001` failure the server surfaces this recovery guidance as a `hint` field on the terminal `error` payload.
- **Start a brand-new session** (start a run without `mentor_session_*`) when you need to reset the OML itself — prior turns left it in a bad state you can't unwind — or you move to an unrelated app; `fresh_context` keeps the edited OML, so it does NOT revert it. A brand-new session re-downloads the pristine tenant OML.
- If mentor refuses or returns empty, rephrase with concrete keys and a smaller scope before retrying.
- For required fields, ask mentor to set `IsMandatory=True` on the input widget and leave the label text bare — the platform paints a single red `*` after the label automatically. Don't ask mentor to put a literal `*` in `Label.Text`; it renders black, theme-blind, and stacks with the platform asterisk.

## Context Service visibility (`owned_only`)

The context lookups index by **visibility**, not ownership: app-scoped queries return owned rows plus rows inherited from referenced libraries (OutSystemsUI, Charts, etc.). Each row carries `isReferenced` and `producerAssetKey`/`producerAssetName`. `owned_only` defaults to `true` when `app` is set, `false` tenant-wide; pass `owned_only: false` with `app` to keep inherited rows.

## Workflows

**Describe an existing app (no OML needed):**
1. If you only have a name, search the apps for it, or pass the name directly to `app` on the context lookups and let it resolve.
2. Run the per-type context lookups in parallel — screens for the UI surface, entities for the data model, actions for logic, roles for security — plus the app's references for dependencies on other modules / external libraries.
3. Synthesize into the user-facing explanation.

**Edit an existing app and ship it:**
1. First turn: start a mentor run with the `app_key` and your prompt (e.g. "Add a due date field to Task"). It returns a `runId`; poll the run with its `cursor` until terminal, then pull `mentor_session_id` + `mentor_session_token` out of the result.
2. Optional follow-up turns: start another run passing `mentor_session_id` + `mentor_session_token` and your next prompt, and poll the same way. Each terminal result returns a fresh token; use the newest one next.
3. Publish the edited OML with `mentor_session_id` + `mentor_session_token` + `env_key`; it returns a publication id. An optional `message` (max 500 chars) attaches a publish note to the created revision — the same note ODC Studio's "1-Click Publish with message" sets; over-length is rejected up front, and attaching the note is best-effort so a failure to attach it doesn't fail the publish.
4. Poll the publication status until terminal. Pull the publication logs for messages on failure.

**Promote a build across environments:**
1. Start a deployment with the asset key, the target `env_key`, and `from_env` for the source (or pin with `build_key` + `revision`); it returns an operation key.
2. Poll the deployment status until terminal.
3. On failure: pull the deployment messages for diagnostics.

**Publish a new external library:**
1. Build a .NET 10 lib with `[OSInterface(Name = "<UniqueName>")]` (reusing a name produces a new revision, not a fresh asset). `dotnet publish -c Release`, zip the `.dll` + `.deps.json` at the zip root (no nested folder). Base64-encode the zip.
2. Upload the library with `zip_b64` and `auto_publish: true`; it returns an operation key.
3. Poll the external-library status until `Published`. On validation failure, pull the operation logs.

**Reference an external library from an app:**
- Just ask mentor: start a run with the `app_key` and a prompt like "Use the <ActionName> action from <LibraryName> in <screen edit>.", then poll the run as usual.

**Run a deployment-impact analysis:**
1. Start the impact analysis with the asset key and `env_key`; it returns an analysis id.
2. Poll the impact-analysis status until terminal, passing `kind: "deployment"`. Use `kind: "deletion"` instead when you started the analysis with `delete: true`.

## Feedback

A `submit_feedback` MCP tool lets you push signal to the OutSystems maintainers about what's working and what isn't. Use it for two reasons.

**Redaction rule (applies to BOTH `value` and `rationale` on every call).** Before passing any text into either field, scan it for and replace each with `[redacted]`:
- Bearer tokens, JWTs, API keys, passwords, OAuth client secrets
- PII (email addresses, full names, phone numbers from any User entity you queried)
- Code snippets and OML
- Full transcripts of multi-turn dialogue

When you redact, tell the user what you replaced.

**User-initiated.** When the user explicitly asks to report something, or when they type `/outsystems-feedback`, expand to a `submit_feedback` call:
- `name`: `"user_feedback"`
- `value`: a one-word categorical tag: `"bug-report"`, `"feature-request"`, `"thumbs-up"`, or `"thumbs-down"`. Pick the tag that best matches the user's message; if it's ambiguous, default to `"bug-report"`. Cap at 256 bytes. **Do NOT** put free-form prose here; the value field is a discrete grouping key. Numeric ratings ("4") and booleans ("true"/"false") are accepted by the server for downstream flexibility, but do not surface them as options in a picker or prompt; users find rating scales less intuitive than named tags.
- `rationale`: the user's words (or your summary if they were verbose), after applying the redaction rule. Cap at 4096 bytes; truncate the tail and tell the user if it was longer.
- `mentor_session_id`: pass the most-recent `mentor_session_id` you've worked with in THIS conversation, when one exists. **Must be a UUID** (server rejects non-UUID strings). Omit when there's no relevant mentor session in scope; the server has a per-user auto-fallback that supplies the most-recent one on this pod.
- `mentor_turn_id`: optional opaque per-turn id (≤256 bytes), one level finer than `mentor_session_id`. Pass the `runId` from the most-recent mentor tool response the user is reacting to. Do NOT guess; if you lost track of which turn the user meant, omit it — silence is safer than a wrong-turn tag. There is NO server-side auto-fallback here (unlike session id); you are the only source of ground truth.
- `experiment_id`: optional opaque A/B experiment tag (≤128 bytes). Include only when the plugin / harness is running an experiment the caller wants tagged. Omit for regular feedback.
- `agent_context`: OPTIONAL structured recap of what you were doing when the user asked for feedback. JSON-encoded string, ≤2048 bytes. Suggested shape:
  ```json
  {
    "recent_tool_calls": [
      {"tool": "context_search", "status": "ok"},
      {"tool": "publish_start", "status": "error", "code": "OS-BEW-1234"}
    ],
    "app_key": "...",
    "env_key": "...",
    "error_details": {
      "message": "verbatim error text from the failing tool response",
      "step": "publish_start"
    }
  }
  ```
  The `error_details` sub-key is a convention (not enforced by the server): when the feedback is about a specific failure, include the verbatim error message + which step it fired on. Downstream triage can slice by `error_details.step` without paraphrasing loss. Redact secrets / PII in `error_details.message` per the redaction step. **Clarify with the user before including.** When the feedback message is clearly about a specific tool interaction (e.g., "the deploy failed"), tell the user "I'll attach a recap of the recent tool calls (env_info, publish_start with code OS-BEW-1234) to help the team reproduce — OK?" and wait for confirmation. When the feedback is general ("love the agent", "thumbs-up"), skip agent_context entirely; there's no useful context to attach.

**Correlation-id offer (mandatory when the user's message hints).** When the user's feedback message contains `session` / `mentor session` (hint for `mentor_session_id`) or `turn` / `mentor turn` / `trace` / `runId` / `run` (hint for `mentor_turn_id`), the agent MUST include an offer in its reply. Silently omitting the correlation without acknowledging the hint is not acceptable.

Preferred flow (interactive session): ask BEFORE submitting.

> "You mentioned a mentor [session|turn] -- do you have the id you want this tied to? If not, I'll submit without it and the server will auto-correlate to your most-recent one where it can."

Wait for the reply. If they respond with an id, attach it verbatim in the corresponding field (`mentor_session_id` must be a UUID; `mentor_turn_id` is opaque ≤256 bytes). If they say no or reply without an id, submit without and do NOT re-ask.

Acceptable alternative when interactive back-and-forth is not possible (fast-path direct-mode invocations, scripted callers): submit with the id null AND include the offer in the confirmation reply so the user can act on it:

> "Sent. If you have the [session|turn] id you want this tied to, share it and I'll resubmit with correlation attached."

What is NOT acceptable: submitting without the id AND without an offer, then only explaining post-hoc that no id was available. The mention of `session` or `turn` is the hint; the agent must honor it.

Scope rules for the offer:
- Only ask about the id-level the user hinted at. `session` in the message does not unlock the `mentor_turn_id` ask, and vice versa.
- Skip the entire offer when the message contains NO such keywords — silent submission is correct.
- Skip the offer when you already have the id in scope from a mentor tool call earlier in this conversation — attach it directly and confirm in the reply which id you attached.
- Do NOT invent or guess ids. If the user replies with a value that isn't shaped like an id (e.g., not a UUID for `mentor_session_id`), tell them and skip the field rather than pass junk.

**Agent-observation (you self-report).** Useful for optimizing tool composition and output quality. Call `submit_feedback` on your own when a situation clearly matches one of the five defined categoricals below. Do NOT fire on routine or expected outcomes (e.g., an empty search result for an obviously-made-up query is NOT `empty_results` — that's a search legitimately returning nothing).

**Scope.** `agent_observation` reports on how OutSystems tools composed to fulfill a specific user request in the current turn. An OutSystems tool is any tool from the connected OutSystems MCP server — the ones that let you inspect and change tenant state. Three invariants must all hold before you fire:

1. **The current user turn contains a task that needs OutSystems tools.** Conversational messages ("thanks", "that's all", "sounds good") are not tasks — no tool composition happened for them, so there is nothing to observe.
2. **You actually called at least one OutSystems tool to fulfill it.** The observation must have a real tool call as its subject. If the turn ran no OutSystems tool, there is no subject.
3. **The subject is a tool interaction, not your own working-out.** Reading guidance, deciding which tool to pick, checking documentation, or otherwise figuring out an approach is not part of the tool composition — the composition is only the tools that actually ran against the OutSystems server. If your draft rationale describes a decision, a lookup, or a step in your reasoning rather than a tool that ran, you have no subject to observe on.

If any invariant fails, do NOT fire — silence is correct, regardless of how well a categorical seems to fit.

The five valid values for `agent_observation` (listed in disambiguation-precedence order — first-match wins when a situation could match multiple):
- `shorter-path-available` — after a multi-step task lands successfully, you spot that a shorter tool sequence would have reached the same result. Fires ONLY post-success; NEVER on a one-step task that already took the direct path. **Threshold**: reserve for shortcuts that generalize to the task PATTERN — a step you took would be unnecessary for anyone doing this KIND of task, given tools that already exist. Do NOT fire for execution-only variance (a call you happened to make more times than needed for this specific input, an ordering that was fine but not optimal). If the shortcut depends on knowing this particular input's shape or size, it's execution detail, not composition insight — skip. **Tie-break vs `unexpected_shape`**: if any step you took returned only data already present in a prior step's output (i.e., that step was redundant in retrospect), this fires — even if the redundant step's response also had a shape quirk. "Missing expected fields" on the redundant step is a symptom; the higher-order insight is that the step wasn't needed.
- `wrong_path` — you picked a suboptimal first tool composition and had to pivot to a different one, OR the user had to explicitly redirect you to a different tool ("just use X directly", "no, try Y instead") because your first pick was wrong, OR your first tool errored because it was fundamentally the wrong tool for the intent. A user redirect after a wrong first pick counts as much as a self-pivot — the signal is the same.
- `repeated_clarification` — the same user intent required 3+ back-and-forth turns of ambiguous user replies before you could act (or you gave up because ambiguity persisted).
- `unexpected_shape` — a tool response was well-formed but lacked expected fields or had an unexpected structure that made it hard to chain into the next call. NOT this if the "missing field" happened on a step that turned out to be redundant post-success — that's `shorter-path-available` (see tie-break above).
- `empty_results` — a tool returned zero results in a case where you had strong reason to expect data. The bar is "surprising empty return", not "any empty return". Searching for a plausible-sounding thing that legitimately doesn't exist is NOT this; searching for something the user just clearly referenced and getting nothing IS.

**Never invent a value.** These 5 are the entire enum. If none clearly fits, do NOT fire — silence is safer than a made-up categorical.

Use:
- `name`: `"agent_observation"`
- `value`: one of the 5 exactly, per the enum above. Rejecting silence is not a valid choice.
- `rationale`: one sentence describing the situation **in your own words**, after applying the redaction rule. Do NOT quote or paraphrase the user's message. Describe what went wrong (or, for `shorter-path-available`, the shortcut you spotted plus the attempts you made before landing the working path). Cap at 4096 bytes.
- `mentor_session_id`: only when the observation is about a mentor turn, and only if you have a UUID.
- `agent_context`: OPTIONAL structured recap of what you were doing when you constructed this observation. JSON-encoded string, ≤2048 bytes. Same shape and secrets rules as user-initiated.

**When to fire.** When any of the five categoricals above clearly matches the just-completed tool interaction, fire it. One row is cheap; silence when a categorical actually applies costs the team a real signal. Do NOT wait for the user to grant permission — the SKILL is the permission. Fire at most one `agent_observation` per user turn.

**When to skip.** Only when NONE of the five categoricals clearly matches AND all three scope invariants hold. If your draft rationale sentence would be about the agent's own workflow rather than a specific OutSystems tool call, skip. If the situation is genuinely borderline and you would have to argue with yourself that it is noteworthy, skip. `shorter-path-available` in particular should stay low-frequency — fires per successful multi-step task, not per turn; never on a one-step task that already took the direct path.

**Positive triggers (fire immediately, do not deliberate)**:
- Just did a lookup for a concrete resource the user named (an app, a deploy, a session) and it returned empty → fire `empty_results`.
- Just called a tool, it errored or returned an unusable shape, you had to fall back to a different tool to make progress → fire `wrong_path`.
- The user's last message corrected your tool choice ("no, use X instead") after you had already picked one → fire `wrong_path`.
- A multi-step task just landed successfully AND one of its steps turned out to be structurally unnecessary (given the input the user handed you upfront) → fire `shorter-path-available`.
- A tool's response is missing fields its description explicitly promised, and you needed those fields to proceed → fire `unexpected_shape`.
- You are on the 3rd back-and-forth clarification about the same user intent → fire `repeated_clarification`.

**Bounded exception: proactive prompt after a clearly-broken failure.** The default rule is "don't volunteer `/outsystems-feedback`", but a real, unexpected failure is signal that would otherwise be lost. Exactly ONCE per user session, after a tool call that returns a 5xx / `MentorTurnOutcome::SubprocessError` / any `OS-BEW-*` or `OS-DPL-*` failure code, you MAY ask the user a single terse question:

> "That failed unexpectedly. Want to send feedback about it? I'd include the tool call, error code, and pod version to help the team reproduce."

The one-line "what will be captured" note is important — users are more willing to file when they know what's shared. Keep it terse; do NOT elaborate into a wall of text.

Rules for the exception:
- Fires at most once per session, no matter how many failures happen.
- Skip when the failure was expected (dry-run, deliberate misconfiguration test, or the user just told you they're testing failure paths).
- Skip when a `server_failure` auto-emit was NOT triggered — those cases aren't "clearly broken", they're user errors.
- If the user says yes, drive the guided-form flow (skip Step 1 — pre-fill category as "Bug report").
- If the user says no or ignores the ask, DO NOT re-ask this session.

**User asking how to give feedback.** When the user asks "how do I file a bug?" / "how do I give feedback?" / "how do I report a problem?", explain that `/outsystems-feedback` is the surface AND offer to invoke it directly: "You can type `/outsystems-feedback` for a guided form, or `/outsystems-feedback <message>` to submit directly. Want me to open the guided form now?" This is an exception to "don't volunteer" — the user asked; walking them through it is helpful, not manipulative.

**Reserved names.** The server rejects `name=server_failure` from client submissions; it's reserved for the server's own auto-emit on tool failures. Use `agent_observation` for agent-initiated failure reports. Other `name` values are accepted as forward compatibility, but stick to `user_feedback` and `agent_observation` unless you have a reason.

Slash command shortcut for users (Claude Code): typing `/outsystems-feedback <message>` drives `submit_feedback` per the rules above (the redaction step applies to both `value` and `rationale`; the slash command body in `commands/outsystems-feedback.md` carries the same rules for the `/outsystems-feedback` entry point). The `outsystems-` prefix avoids the collision with Claude Code's built-in `/feedback`, which routes to Anthropic's issue tracker and would shadow an unprefixed plugin command.
