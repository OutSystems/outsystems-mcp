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
- The refreshed `mentor_session_token` only appears in the terminal run result (alongside `mentor_session_id`, `summary`, and `events`). Use the newest token on the next start.
- Sessions auto-GC after 30 min idle. Resuming after GC transparently re-downloads the OML; same `mentor_session_id` and conversation continue.
- To publish the edited OML you need `mentor_session_id` + `mentor_session_token` from the most recent terminal-success run result.

**Pacing polls:**

- Poll the run **immediately** after starting it, and again immediately while the cursor advances — mentor events are cursor-paged and arrive in batches.
- Pause only when the cursor is drained and `status` isn't terminal. **~30s is a reference for mentor**, not a target — without one, agents tend to drift to 60–180s. Publish, deployment, and external-library status polls finish faster; **5–15s** is fine for those.

**When to use the mentor flow vs the context lookups:**
- For *info* about an app, prefer the context lookups. Lightweight, structured, no OML download. Only fall back to mentor when context can't answer (deep OML internals, logic flow traversal).
- For *edits*, the mentor flow is the only path.
- Reuse the same session across follow-up turns in one task; the server-side OML and tool history stay loaded.
- Start a fresh session (start a run without `mentor_session_*`) when: (a) mentor hallucinates entities/actions that don't exist; (b) you switch to an unrelated task on the same app; or (c) prior turns left the OML in a bad state.
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
3. Publish the edited OML with `mentor_session_id` + `mentor_session_token` + `env_key`; it returns a publication id.
4. Poll the publication status until terminal. Pull the publication logs for messages on failure.

**Promote a build across environments:**
1. Start a deployment with the asset key, the target `env_key`, and `from_env` for the source (or pin with `build_key` + `revision`); it returns an operation key.
2. Poll the deployment status until terminal.
3. On failure: pull the deployment messages for diagnostics.

**Publish a new external library:**
1. Build a .NET 8 lib with `[OSInterface(Name = "<UniqueName>")]` (reusing a name produces a new revision, not a fresh asset). `dotnet publish -c Release`, zip the `.dll` + `.deps.json` at the zip root (no nested folder). Base64-encode the zip.
2. Upload the library with `zip_b64` and `auto_publish: true`; it returns an operation key.
3. Poll the external-library status until `Published`. On validation failure, pull the operation logs.

**Reference an external library from an app:**
- Just ask mentor: start a run with the `app_key` and a prompt like "Use the <ActionName> action from <LibraryName> in <screen edit>.", then poll the run as usual.

**Run a deployment-impact analysis:**
1. Start the impact analysis with the asset key and `env_key`; it returns an analysis id.
2. Poll the impact-analysis status until terminal, passing `kind: "deployment"`. Use `kind: "deletion"` instead when you started the analysis with `delete: true`.
