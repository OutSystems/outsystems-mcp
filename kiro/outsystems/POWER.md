---
name: "outsystems"
displayName: "OutSystems - MCP"
description: "Drive OutSystems from Kiro over the MCP HTTP transport: edit apps, publish, deploy, search tenant elements, manage external libraries."
keywords: [outsystems, low-code, oml, deployment, mcp]
author: "OutSystems AI Platform"
---

# OutSystems — MCP

## Overview

OutSystems is a cloud-native low-code platform where apps are built from OML (OutSystems Model Language) — a binary format describing entities, screens, actions, and logic. This Power connects Kiro to the **OutSystems MCP server**: a hosted, multi-tenant HTTP transport that exposes the full OutSystems tool surface across apps, context lookups, mentor-driven editing, publishing, deployments, external libraries, and environments.

There is no CLI to install. There is no OML on disk. OML stays server-side; you edit through the mentor flow (start a run, then poll it to terminal) and ship via the publish tool.

## Onboarding

### Prerequisites

- Kiro 0.11.133 or newer.
- A web browser on the same machine as Kiro (Kiro picks an ephemeral local port for the OAuth callback after Dynamic Client Registration).
- An OutSystems tenant hostname (e.g. `mycompany.outsystems.dev`).
- Network access to the OutSystems tenant hostname (e.g. `*.outsystems.dev`).
- Your tenant enabled for the OutSystems MCP server. This is a server-side allowlist, so if it is not enabled every tool call is rejected with `tenant_not_allowed` however the Power is installed.

### Installation

This Power doesn't ship its own MCP server config. The first time you ask Kiro Chat to do something with OutSystems, the agent will notice no `outsystems` MCP server is registered, ask you for your tenant hostname, and add an entry to Kiro's user-level `~/.kiro/settings/mcp.json`. No script, no shell command. Just install the Power and start chatting.

Two ways to install the Power into Kiro:

Both snippets below omit `iconUrl` — the Power installs but shows no logo in Kiro's Powers UI. To enable the logo, add `"iconUrl": "data:image/png;base64,<base64-encoded contents of kiro/outsystems/icon.png>"` to the registry JSON (Kiro's webview CSP blocks `file://`, so a data URL is required). Encode with `base64 -w0` on Linux or `base64 -i` on macOS.

**Option A - clone locally, point Kiro at the local copy.** Most deterministic; doesn't depend on Kiro shelling out to git.

```bash
# 1. Clone the repo somewhere (keep this clone — Kiro reads from it)
git clone https://github.com/OutSystems/outsystems-mcp ~/git/outsystems-mcp

# 2. Drop a registry pointer that references the local clone
mkdir -p ~/.kiro/powers/registries
cat > ~/.kiro/powers/registries/outsystems.json <<EOF
{
  "name": "OutSystems",
  "type": "local",
  "powers": [{
    "name": "outsystems",
    "displayName": "OutSystems - MCP",
    "description": "Edit, publish, deploy OutSystems apps from your AI assistant.",
    "source": {"type": "local", "path": "$HOME/git/outsystems-mcp/kiro/outsystems"},
    "autoInstall": true
  }]
}
EOF
```

**Option B - let Kiro clone the repo itself.** Simpler; works over anonymous HTTPS.

```bash
mkdir -p ~/.kiro/powers/registries
cat > ~/.kiro/powers/registries/outsystems.json <<EOF
{
  "name": "OutSystems",
  "type": "local",
  "powers": [{
    "name": "outsystems",
    "displayName": "OutSystems - MCP",
    "description": "Edit, publish, deploy OutSystems apps from your AI assistant.",
    "source": {
      "type": "repo",
      "repositoryCloneUrl": "https://github.com/OutSystems/outsystems-mcp",
      "pathInRepo": "kiro/outsystems",
      "repositoryBranch": "main"
    },
    "autoInstall": true
  }]
}
EOF
```

Restart Kiro after dropping the registry file. On startup Kiro auto-installs the Power: it copies `POWER.md` and `steering/skill.md` into `~/.kiro/powers/installed/outsystems/`. The Power appears in Kiro's Powers UI; the MCP server itself gets registered by the agent on first use (see the steering content).

Then open Kiro Chat and ask it for anything OutSystems-related; the steering content takes over and the agent walks you through the tenant prompt + OAuth on first use.

### Switching tenants

Just tell Kiro Chat "switch OutSystems to a different tenant" (or similar). The agent will repeat the tenant prompt and update `mcpServers.outsystems.url` in `~/.kiro/settings/mcp.json`. Kiro's file watcher reloads MCP automatically.

## Common Workflows

Workflows below describe the call sequence in prose; read the live `tools/list` for exact tool names, arguments, and response shapes — this Power names domains, not tools. Identity (tenant + user) is derived from the validated bearer JWT — none of the tools take a `tenant` argument.

### Workflow 1: Describe an existing app

1. Resolve the app: search for it by name, or pass the name directly where an app is expected and let it resolve to a key.
2. In parallel, gather context (independent calls):
   - the UI surface (screens)
   - the data model (entities)
   - the logic (actions)
   - security (roles)
   - dependencies on libraries / other modules (the app's references)
3. Synthesize for the user.

### Workflow 2: Edit an app and ship it

1. Open a mentor session on the app and send a prompt describing the change (e.g. "Add a due date field to Task") → returns `runId`. The catalog says where the app goes in; a prompt sent before the session has an app has nothing to edit, and a session runs one turn at a time, so a start that appears to do nothing while a run is live means poll the run you already have. Poll the run until terminal.
2. Keep the session handle from whichever response handed it to you and pass it, unchanged, into the next turn; if a later response — a failed turn's included — hands you a newer one, the newest wins. A failed turn ends neither the conversation nor its committed state, so continue in the same session rather than opening another; open a fresh one only when the error says the session is gone or when you deliberately want the pristine tenant OML back, and when the failure happened during session setup, before it held the app, redo that setup step instead. If the conversation hits its max length or mentor starts hallucinating, reset the conversation rather than the session: if the catalog offers a way to start a fresh conversation over the session's current OML, use it — it keeps the session and any unpublished edits; if it doesn't, publish first and then open a fresh session. Before reporting a turn done, read the completion signals on the terminal payload (change attempted, change applied, validation errors); `succeeded` alone means the turn ended.
3. Publish → returns a publication identifier. The publish call identifies the app through the session it is given, so pass the session handle and never an app key; where the catalog offers a target environment, pass it, otherwise the publish lands in the development environment. An optional publish note (the catalog names the field; max 500 chars) attaches to the created revision — the same note ODC Studio's "1-Click Publish with message" sets.
4. Poll the publication status until terminal. On failure, pull the publication logs. **A `failed` carrying `indeterminate: true` is not a confirmed failure** — the server lost sight of the publish, so it may still be building and may yet succeed. Do NOT re-publish on that (a second publish on the same app while the first is still running is what wedges an app); re-poll the publish status with the `publication_key` from the payload, or verify via the environment's app info, and only then decide.
5. Release the session once the publish has landed, if the surface gives you a way to — releasing discards anything unpublished, and a session left open holds its resources until it times out.

### Workflow 3: Promote a build across environments

1. Start a deployment with the asset key, the target `env_key`, and `from_env` for the source (or pin with `build_key` + `revision`) → returns operation key.
2. Poll the deployment status until terminal.
3. On failure: pull the deployment messages for diagnostics.

### Workflow 4: Publish a new external library

1. Build a .NET 8 lib with `[OSInterface(Name = "<UniqueName>")]`. `dotnet publish -c Release`, zip `.dll` + `.deps.json` at the zip root, base64-encode it.
2. Upload the library with `zip_b64` → returns operation key.
3. Poll the external-library status until `ReadyForReview`. On validation failure, pull the operation logs.
4. Publish the operation with that same operation key, then poll the status until `Published`.

## Conventions

- **OML is server-side.** There is no download tool. Use the app's references plus the context lookups for inspection; the mentor flow (start a run, then poll it to terminal) for edits. When a user asks for the OML on disk, say plainly that the remote MCP transport does not expose a file-to-local-disk download (the server has no local filesystem to write to), and where useful offer the partially answerable portion (e.g. the app's revision history for the latest version number).
- **The mentor call sequence differs between tenants.** How many calls a mentor task takes, and what each one takes, is the catalog's to say: read `tools/list` and follow what it advertises. A mentor tool rejected as unavailable for this tenant means the sequence was assumed rather than read — it is not a broken server, a lapsed sign-in, or an unenrolled user.
- **No selected environment.** Every environment-scoped tool takes `env_key` per call; the transport is stateless by design. When a user asks for a session-persistent `env select` style toggle, say so explicitly rather than refusing silently, and reframe the request so they pass `env_key` per call.
- **No local CWD.** The server has no view of the caller's filesystem. When a user asks about local paths, working directories, or CWD-relative artifacts, state the limit plainly and surface the closest server-side data inline (e.g. paste the environment-list payload back so the user can save it themselves) instead of attempting the operation. Don't silently route a write or a read through a non-MCP tool; the architectural fact has to reach the user.
- **Operations return immediately.** Every deployment operation, publishing, and every external-library operation returns an id; poll the matching status surface until it's terminal.
- **Never invent IDs.** App keys, env keys, build keys, operation keys are opaque. Resolve them via the listing and lookup calls, or ask the user.
- **Only `status` says a run finished.** `complete` is an event name that appears while the run is still going, and a cancel still in progress is non-terminal too, so neither means the turn is done. A run abandoned before `status` reaches `succeeded`, `failed`, or `cancelled` never shows its completion signals, and anything its terminal payload carries for the next call is lost with it. An error on a poll is not a dead run either: a stale-cursor error just means the cursor went stale over a long pause, and re-polling the way the tool's description says picks the run back up.
- **A `tenant_not_allowed` rejection is a server-side per-tenant allowlist gate, not a lapsed sign-in.** The token is valid, so re-authenticating, re-registering, and removing and re-adding the server all fail identically while risking a working configuration. Confirm with the user which host the server is pointed at, because a right account on the wrong tenant gets this same rejection and is fixed by pointing it at the right one. If the host is right, tell the user to ask their OutSystems contact to have the tenant enabled.

## Troubleshooting

### MCP server unreachable

**Symptom:** Kiro reports the `outsystems` server as not configured / not connected, or tools return `tenant not configured` errors. A rejection naming `tenant_not_allowed` is a different condition. Use step 2 to check the configured URL is the tenant you mean, because a correctly enabled account pointed at the wrong tenant gets this same rejection. If the host is right, no remaining step changes it: ask your OutSystems contact to have the tenant enabled.

**Solutions:**
1. Have you completed the first-use tenant prompt? Open Kiro Chat and ask anything OutSystems-related; the agent will notice the missing server entry and walk you through it.
2. Verify the install: `jq '.installedPowers[] | select(.name=="outsystems")' ~/.kiro/powers/installed.json` should return the entry, and `jq '.mcpServers.outsystems' ~/.kiro/settings/mcp.json` should return an object with a `https://<your-tenant>/mcp` URL.
3. If there's no `outsystems` entry under top-level `mcpServers`, the tenant prompt was skipped or interrupted. Tell Kiro Chat "set up OutSystems again" and complete the flow.
4. Verify network reachability: `curl -I "<URL-from-settings>"` should return an HTTP response (likely 401 without a bearer; that's expected and means routing works).

### OAuth doesn't open / callback fails

**Symptom:** Browser tab doesn't open, OR the browser shows "site can't be reached" / a redirect-uri mismatch on the `localhost:<port>/callback` page. None of this applies to a rejection naming `tenant_not_allowed`, where sign-in already succeeds; see Conventions.

**Solutions:**
1. **Browser didn't open at all:** re-trigger the sign-in — ask Kiro Chat to retry the OutSystems action (the first tool call re-initiates OAuth), or authenticate the `outsystems` server from Kiro's MCP UI. Kiro owns the OAuth flow.
2. **Callback page shows "site can't be reached":** Kiro listens on an ephemeral `localhost` port for the callback, so a browser must be reachable on the same machine as Kiro (see Prerequisites). On a remote/SSH session without a local browser, run Kiro where a browser can reach `localhost` and retry.
3. **DCR or auth-handshake errors:** surface the error message verbatim and file an issue against `OutSystems/outsystems-mcp` with the symptoms.
4. **Last resort:** remove and re-add the `outsystems` server in Kiro's MCP UI to wipe stale OAuth state, then ask Kiro Chat to redo the first-use steering flow. Do not do this for a `tenant_not_allowed` rejection: it discards a working configuration without affecting the tenant allowlist.

### Tool errors

Errors carry a structured category in `data.category` (`AuthError`, `ValidationError`, `UpstreamError`, `InternalError`); upstream errors also include `data.upstream_status`. Use these for retry decisions, not the message text. Three named exceptions: the external-library `Server is busy, retry shortly` case, which is transient and worth retrying; a rejection naming `tenant_not_allowed`, which no retry or re-setup clears, covered under Conventions; and a `tenant not configured` error, a setup fault covered under MCP server unreachable above, not a retry target.

## Limitations

- **No OML download on this transport.** OML stays in the server-side mentor session and never crosses the wire as bytes.
- **No per-session "selected environment".** Every environment-scoped tool takes `env_key` per call.
- **Long-running tools return immediately.** Every deployment operation, publishing, and every external-library operation returns an id; you must poll the matching status surface until it's terminal.
- **An idle mentor session does not live forever.** A short pause resumes where it left off, and the first turn after it may be slower; after the server's idle limit the session is gone, the error says so, and unpublished edits went with it. Publish before a long pause.
- **An open mentor session holds server resources.** One left open holds them until it times out, so release it once its work is published if the surface offers a way to — releasing discards anything unpublished.

## Configuration files

The Power's installed state (created by Kiro's auto-install when it processes the registry file):

| Path | Purpose |
|---|---|
| `~/.kiro/powers/registries/outsystems.json` | LocalRegistrySchema; points at the Power source. |
| `~/.kiro/powers/installed.json` | Lists `outsystems` as installed. |
| `~/.kiro/powers/installed/outsystems/POWER.md` | This file (copied from source). |
| `~/.kiro/powers/installed/outsystems/steering/skill.md` | Agent-facing skill content; loads into the chat agent's context whenever the Power is active. Drives the tenant prompt + MCP wiring + OAuth. |
| `~/.kiro/settings/mcp.json` | Kiro's MCP loader file. The agent writes the tenant URL to top-level `mcpServers.outsystems` here on first use. The Power has no per-install `mcp.json`, so Kiro's update flow can't corrupt the tenant URL. |

