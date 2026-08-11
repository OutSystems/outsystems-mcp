# outsystems-mcp

Distribution repo for the OutSystems MCP. To install, paste the matching prompt below into your AI assistant.

## ⚠️ Disclaimer
> Early Alpha. Please Read Before Using
> This project is in early alpha and is provided as-is, without warranties or guarantees of any kind. It is not production-ready, expect bugs, incomplete features, breaking changes, and unstable behaviors. Do not rely on it for critical, commercial, or production use.
> No support, SLAs, or maintenance commitments are offered. We are sharing this publicly because we value community input, not because it is ready for broad adoption.
> Bug reports, feature requests, and feedback are welcome, feel free to open an issue. Responses and fixes happen on a best-effort basis with no defined timeline.

## Install - Claude Code

Paste into Claude Code:

```
Install the OutSystems outsystems-mcp plugin from OutSystems/outsystems-mcp on GitHub.
Step 1: run `claude plugin marketplace add OutSystems/outsystems-mcp`.
Step 2: run `claude plugin install outsystems@outsystems`.
Step 3: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 4: when I tell you, run `claude mcp add -s user --transport http outsystems https://<my-tenant>/mcp` (substitute my actual tenant for `<my-tenant>`). Add no `--client-id` and no `--callback-port`: the server supports OAuth Dynamic Client Registration, so Claude Code registers its own client on an ephemeral loopback port.
Step 5: tell me to restart Claude Code, then ask anything OutSystems-related; you'll drive the OAuth flow automatically via Claude Code's synthesized `authenticate` tool (a client convenience, not a server tool). If that doesn't trigger, or a call fails with an auth error, tell me to run `/mcp -> outsystems -> Authenticate` manually as the fallback.
```

After install, you can also type `/outsystems-feedback <message>` in Claude Code to send feedback about the agent experience so the maintainers can act on it. The slash command is Claude-Code-only (and uses the `outsystems-` prefix so it doesn't collide with Claude Code's built-in `/feedback`, which routes to Anthropic's issue tracker); on other harnesses, ask the agent in plain language ("send a thumbs-up about the OutSystems agent") and it will invoke the underlying `submit_feedback` MCP tool.

## Install - Claude Desktop

Claude Desktop connects to remote MCP servers natively, so there is nothing to install and no config file to edit. Do this in the UI:

1. Open **Settings > Connectors**.
2. Click **Add custom connector**.
3. Enter `https://<my-tenant>/mcp`, substituting your OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
4. Click **Add**. The first OutSystems tool call opens a browser for OAuth sign-in.

Available on Free, Pro, Max, Team and Enterprise, with Free limited to one custom connector.

**On a Team or Enterprise plan you may not see "Add custom connector" at all.** Adding custom connectors is an organization-level permission: an Owner adds the connector in **Admin settings > Connectors** and members then click **Connect** on it. If your organization has custom connectors disabled entirely, no member can add one and neither can an Owner without changing that policy. Ask an organization Owner before assuming the connector path is unavailable to you.

<details>
<summary>Fallback: organization policy blocks custom connectors, or your tenant is not reachable from the public internet</summary>

Two situations need a local proxy instead:

- Your organization disallows custom connectors.
- Your tenant is VPN-only or IP-allowlisted. A custom connector is reached from Anthropic's cloud rather than from your machine, so Anthropic cannot connect to a tenant that is not publicly reachable.

Paste into Claude Desktop (requires Node.js with `npx` available on your machine):

```
Install the OutSystems MCP server in Claude Desktop via a local proxy.
Step 1: install `mcp-remote` globally: `npm install -g mcp-remote`. This is idempotent, safe to run even if already installed.
Step 2: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 3: locate the Claude Desktop config file. macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows: `%APPDATA%\Claude\claude_desktop_config.json`. Read the file (start from `{}` if it doesn't exist). Preserve every existing key. Patch the top-level `mcpServers` object by adding or replacing the `outsystems` entry:
  - macOS/Linux: `{"command": "npx", "args": ["mcp-remote", "https://<my-tenant>/mcp"]}`
  - Windows: `{"command": "cmd", "args": ["/c", "npx mcp-remote https://<my-tenant>/mcp"]}`
Substitute my actual tenant hostname for `<my-tenant>`. Write the file back.
Step 4: tell me to restart Claude Desktop. After restarting, the first OutSystems tool call will open a browser window for OAuth sign-in; complete the sign-in when prompted.
```

Claude Desktop launches processes with a minimal PATH, so `npx` may not be found even if it works in your terminal. If the server fails to connect after restart, find the full path to `npx` (run `which npx` on macOS/Linux or `where npx` on Windows) and replace `"npx"` in the config with that full path (e.g. `/opt/homebrew/bin/npx`).

</details>

> **Note:** neither path installs the OutSystems conventions doc, so Claude Desktop gets the tools without the usage guidance the other harnesses receive. Read [SKILL.md](SKILL.md) if you want the conventions, and expect to confirm destructive operations yourself rather than being prompted.

## Install - Kiro Chat

Install the Power yourself from the Powers panel: **Add Custom Power** > **Import power from GitHub**, paste the URL below, then **Install**.

```
https://github.com/OutSystems/outsystems-mcp/tree/main/kiro/outsystems
```

Then paste into Kiro Chat:

```
Finish setting up the OutSystems Power in Kiro.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: when I tell you, set the URL `https://<my-tenant>/mcp` in ~/.kiro/settings/mcp.json under top-level `mcpServers.outsystems` (read first, preserve every other entry): `{"type": "http", "url": "https://<my-tenant>/mcp"}`.
Step 3: tell me the OAuth sign-in opens automatically on the next OutSystems tool call. Kiro runs the flow itself and opens the browser for the localhost callback; I just complete the sign-in when prompted. There is no `authenticate` tool to call in Kiro.
```

The tenant URL goes under the **top-level** `mcpServers`, not under `powers.mcpServers`. Kiro rewrites the whole `powers` block on every Power install, uninstall or update, so a URL stored there is lost on the next update; a URL at the top level is untouched.

<details>
<summary>Alternative: install via a registry file (adds the icon to the Powers list)</summary>

The GitHub import registers the Power without an icon. If you want the OutSystems logo in the Powers list, register it yourself instead. Paste into Kiro Chat:

```
Install the OutSystems Power from https://github.com/OutSystems/outsystems-mcp.
Step 1: clone the repo to ~/git/outsystems-mcp if it isn't there yet: `git clone https://github.com/OutSystems/outsystems-mcp.git ~/git/outsystems-mcp`.
Step 2: base64-encode ~/git/outsystems-mcp/kiro/outsystems/icon.png with `base64 -w0` (Linux) or `base64 -i` (macOS). Then write ~/.kiro/powers/registries/outsystems.json with this content (substitute the literal value of $HOME, and inline the base64 string in place of <ICON_BASE64>):
{"name":"OutSystems","type":"local","powers":[{"name":"outsystems","displayName":"OutSystems - MCP","description":"Edit, publish, deploy OutSystems apps from your AI assistant.","iconUrl":"data:image/png;base64,<ICON_BASE64>","source":{"type":"local","path":"$HOME/git/outsystems-mcp/kiro/outsystems"},"autoInstall":true}]}
Step 3: Kiro watches that directory and installs the Power within a few seconds. Restart only if it doesn't appear.
Step 4: then complete Steps 1 to 3 of the main recipe above to set the tenant URL.
```

The icon has to be inlined as base64 because Kiro's Powers view only loads images from `data:` URIs or its own CDN, so a `raw.githubusercontent.com` URL will not render.

</details>

## Install - Copilot in VS Code

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

One-click: [**Add the OutSystems MCP server to VS Code**](https://vscode.dev/redirect/mcp/install?name=outsystems&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2F%24%7Binput%3Aos_tenant%7D%2Fmcp%22%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22os_tenant%22%2C%22description%22%3A%22Your%20OutSystems%20tenant%20hostname%20%28e.g.%20mycompany.outsystems.dev%29%22%7D%5D). VS Code prompts you for your tenant hostname the first time the server starts and remembers it after that. You still need the conventions doc, so run Step 3 of the recipe below afterwards.

Or paste into VS Code copilot chat:

```
Install the OutSystems MCP server in VS Code Copilot.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: open my user MCP config (behind `MCP: Open User Configuration`) or create `.vscode/mcp.json`. Read it first and preserve existing entries, then add under the top-level `servers` object (the key is `servers`, NOT `mcpServers`) the canonical `servers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json), substituting my tenant for `<my-tenant>`:
{"outsystems": {"type": "http", "url": "https://<my-tenant>/mcp"}}
Do NOT add an `oauth.clientId` — the server supports Dynamic Client Registration and VS Code registers its own client automatically.
Step 3: install the OutSystems conventions file: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes to `.github/copilot-instructions.md` in my workspace. Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file already exists do NOT hand-merge; save the copy alongside it and tell me.
Step 4: tell me to open the MCP config I edited (either `.vscode/mcp.json` or the user configuration behind `MCP: Open User Configuration`), check for `outsystems` under `servers`, and start it. A browser opens automatically for OAuth on first connection.
Step 5: then tell me to ask `list 10 of my outsystems apps` to ensure it is working
```

## Install - Copilot in CLI

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

Paste into copilot:

```
Install the OutSystems MCP server in Copilot CLI.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: run `copilot mcp add --transport http outsystems https://<my-tenant>/mcp` (substitute my tenant). This writes the server to `~/.copilot/mcp-config.json` under the top-level `mcpServers` object — it's added to config, but a CLI session that's already running won't load it until Step 4. This matches the canonical `mcpServers.outsystems` block at https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json. Add no auth headers or client_id; the server uses OAuth + Dynamic Client Registration.
Step 3: install the OutSystems conventions file: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes to `.github/copilot-instructions.md` in the working directory (or `AGENTS.md` if the project uses that). Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file already exists do NOT hand-merge; save the copy alongside it and tell me.
Step 4: since `copilot mcp add` wrote the server to config from outside this running session, the session hasn't loaded it yet. Tell me to type `/mcp reload` in the CLI to load it (then optionally `/mcp show outsystems` to confirm it's listed). Note: `/mcp ...` are interactive slash commands I type in the REPL — you cannot run them for me, so ask me to run them rather than executing them yourself. The OAuth flow runs on the first OutSystems tool call — a browser opens for me to authorize.
Step 5: once the tools are listed, tell me to ask `list 10 of my outsystems apps` to ensure it is working.
````

## Install - Copilot in Visual Studio (Windows)

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

Paste into copilot chat:

```
Install the OutSystems MCP server in Visual Studio Copilot.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: create or edit `.mcp.json` in my solution dir (`<SolutionDir>\.mcp.json`) or global `%USERPROFILE%\.mcp.json`. Read it first and preserve existing entries, then add under the top-level `servers` object the canonical `servers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json), substituting my tenant:
{"outsystems": {"type": "http", "url": "https://<my-tenant>/mcp"}}
Do NOT add an `oauth.clientId` — the server supports Dynamic Client Registration.
Step 3: install the OutSystems conventions file by DOWNLOADING it — do NOT read it into chat and retype it. Run this terminal command from the repo root (approve it when Visual Studio asks): `New-Item -ItemType Directory -Force .github | Out-Null; Invoke-WebRequest -Uri https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md -OutFile .github\copilot-instructions.md`. Then verify it downloaded fully — `(Get-Content .github\copilot-instructions.md).Count` should report ~150+ lines; if it's short, re-run the command, never hand-type the content.
Step 4: tell me to open the Tools picker, and ENABLE the `outsystems` tools — in Visual Studio, MCP tools are disabled by default and must be turned on manually. It will fail due to authentication, click "view details" and follow the steps in the authentication section. Finally, enable all tools.
Step 5: tell me to ask `list 10 of my outsystems apps` to ensure it is working.
```

## Install - Cursor CLI

Paste into Cursor agent:

```
Install the OutSystems MCP server in Cursor CLI.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: create or edit `~/.cursor/mcp.json` (global config) or `.cursor/mcp.json` (project config, takes precedence). Read it first and preserve existing entries, then add under the top-level `mcpServers` object (NOT `servers`) the canonical `mcpServers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/mcp.json), substituting my tenant for `<my-tenant>`:
{"outsystems": {"url": "https://<my-tenant>/mcp"}}
Important: use `mcpServers` as the key (not `servers`), and omit `"type": "http"` — Cursor CLI expects this exact format.
Ignore any other mcp config and prefer project config.
Step 3: install the OutSystems conventions file: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/skills/outsystems/SKILL.md and save its exact bytes to `.cursor/rules/outsystems.md` in my workspace root (or `AGENTS.md` if my project uses that). Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file already exists do NOT hand-merge; save the copy alongside it and tell me.
Step 4: in a terminal, run: `agent mcp list` (verify outsystems appears), then `agent mcp enable outsystems` if it shows "needs approval", then `agent mcp login outsystems` (opens browser for OAuth sign-in; complete it there).
Step 5: once logged in, ask `list 10 of my outsystems apps` to ensure it is working.
```

## Install - Cursor App (Plugin)

> **Team/Enterprise plans only:** Requires team admin to import plugin to Team Marketplace.

**Team Admin:** Import the plugin to your Marketplace:
1. Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → **Import from Repo**
2. Enter: `https://github.com/OutSystems/outsystems-mcp`
3. Review the `outsystems` plugin and save (Default On / Required as needed).

**Individual User (after admin installs):** Open Cursor and ask anything OutSystems-related. The agent prompts for your tenant hostname and completes setup automatically.

See [cursor/README.md](cursor/README.md) for detailed setup instructions and version alignment requirements.

## Install - M365 Copilot (web browser)

Currently, this assistant does not support custom MCP servers.

## Install - other AI assistants (best effort)

For other agentic harnesses (Codex CLI, Continue, Cline, Aider, etc.), this is a best-effort install path — the MCP server is a stock streamable-HTTP MCP endpoint with OAuth + Dynamic Client Registration, so most harnesses should be able to wire it up, but we don't validate the flow ourselves. If something breaks, file an issue with the symptoms.

Paste into your harness:

```
Install the OutSystems MCP server.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: register `outsystems` as an MCP server in this harness's configuration, pointing at `https://<my-tenant>/mcp` over the streamable HTTP transport. Use whatever wiring the harness prefers — a CLI command (similar to Claude Code's `claude mcp add`), a settings UI, or hand-editing the harness's MCP config file. The server requires OAuth and supports Dynamic Client Registration, so no shared `client_id` setup is needed, and do not pin a fixed callback port: let the harness pick its own loopback port.
Step 3: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/SKILL.md and inject its contents into this harness's instructions/rules/system-prompt mechanism (e.g. the system prompt rules file in Cline, a repo instruction file consumed by Aider, the system prompt config for Continue, etc.). The skill covers conventions (OML stays server-side, polling shape for long-running tools, error category enums, mentor session round-trip) that the tool descriptions alone don't fully convey.
Step 4: trigger authentication. If the harness synthesizes per-server `authenticate` / `complete_authentication` tools after registration (as Claude Code does — they're a client convenience, not server tools), call those (lazy on first tool call). Otherwise let the harness's built-in MCP auth UI handle the OAuth handshake.
Step 5: depending on the harness, the new MCP server may not be visible until you reload its MCP config or restart. If the harness has a CLI to list registered MCP servers (similar to `claude mcp list`), run it to check whether `outsystems` is visible — if not, tell me to restart the harness. Once the tools appear, ask me anything OutSystems-related to confirm the install is complete.
```

## Troubleshooting

| Symptom | Cause and fix |
| :-- | :-- |
| Tool calls fail with `403` and `tenant_not_allowed` | Your tenant is not yet enabled for the MCP server. This is a server-side allowlist and no amount of reinstalling changes it. Ask your OutSystems contact to have the tenant enabled, or open an issue here with the tenant hostname. |
| The `authenticate` tool isn't loaded (Claude Code) | The MCP server isn't registered, or the session started before it was. Run `claude mcp list` and confirm `outsystems` appears. If it does, restart Claude Code. If it doesn't, re-run Step 4 of the Claude Code recipe. |
| Auth fails with `OAuth callback port <port> is already in use ...` (Claude Code) | An earlier setup step pinned a fixed callback port, and the pin sits in your own config, so updating the plugin does not clear it. Run `claude mcp get outsystems` and note the reported URL, which you need to re-add. If it reports a `callback_port`, unpin it in the reset below. If it does not, the pin is not in your MCP config: check for a callback-port override in your environment, then for another process holding the port with `lsof -nP -iTCP:<port> -sTCP:LISTEN`, or `netstat -ano \| findstr :<port>` on Windows. |
| Auth never triggers in a non-interactive session | The OAuth flow needs a browser and a loopback callback, so it cannot complete in a headless or piped session. Authenticate once in an interactive session first; the token is reused afterwards. |
| "Server Disconnected" or "failed authorization" | Usually a stale or partial OAuth grant. Run the reset below. If it persists, the tenant hostname is likely wrong: confirm it resolves and that `https://<my-tenant>/mcp` returns `401` rather than `404`. |
| Nothing connects on Windows, or `npx` is "not found" | Applies to the Claude Desktop local-proxy fallback only. Claude Desktop launches processes with a minimal PATH. Replace `"npx"` in the config with the absolute path from `where npx`. |
| Browser windows keep reopening, and the proxy log shows `EADDRINUSE` | Applies whenever you reach the server through the `mcp-remote` proxy, which is the Claude Desktop fallback above and any harness you wired up that way. The proxy reuses the callback port saved in its own client registration and exits before sign-in completes, so the host restarts it and no token is ever stored. Clear the saved registration, in the reset below. |
| Tools are listed but greyed out (Visual Studio) | MCP tools are disabled by default. Enable them in the Tools picker. |
| Nothing appears at all on a Copilot Business or Enterprise plan | An admin must enable the "MCP servers in Copilot" policy. |
| No "Add custom connector" button in Claude Desktop | Adding custom connectors is an organization-level permission. An Owner adds it in **Admin settings > Connectors**, or your organization has custom connectors disabled. Use the local-proxy fallback in the Claude Desktop section meanwhile. |

### Reset

When an install is wedged and updates don't stick, do a clean cycle rather than reinstalling on top:

1. Write down the whole `outsystems` entry first, on any harness, because removing it destroys the only record of your tenant URL and of any extra proxy arguments, and later steps need both. On Claude Code, `claude mcp get outsystems` prints the URL and the scope. Then remove the server: `claude mcp remove outsystems`, or delete the `outsystems` entry from the relevant config file on other harnesses. Removing it is also what drops a callback port pinned by an earlier setup step. Omitting `-s` clears whichever scope holds the entry; if the name exists in more than one the command removes nothing and lists them, so repeat it per scope with `-s <scope>`, and leave a `project` scope alone if the config is shared with other people.
2. Uninstall the plugin or Power, if you installed one.
3. Clear the host's cache (in Claude Desktop: **Help > Troubleshooting > Clear cache**). If you reach the server through the `mcp-remote` proxy, also do the following before restarting.

   <details>
   <summary>Clear the saved proxy registration, only if you reach the server through the mcp-remote proxy</summary>

   The proxy saves its own OAuth client registration under `~/.mcp-auth`, and that record pins the callback port it reuses on every later launch. You do not need to touch that store to clear it: give the proxy a different port on the command line and it discards the stale registration itself.

   1. Quit the host, so it stops relaunching the proxy while you work.
   2. Pick a port nothing is using. `lsof -nP -iTCP:<port> -sTCP:LISTEN` on macOS or Linux, `netstat -ano | findstr :<port>` on Windows, should print nothing for it.
   3. Add that port as the last argument of the `outsystems` entry in the host's config, after the URL, for example `{"command": "npx", "args": ["mcp-remote", "https://<my-tenant>/mcp", "<free port>"]}`.
   4. Continue with step 4 of the reset. On the next launch the proxy sees a port that disagrees with its saved registration, deletes that registration, and registers again on the port you gave it.

   The proxy always records some port, so this replaces a stuck one rather than switching pinning off; that is an upstream limitation rather than a setting. Removing the argument again later just makes the proxy reuse the port it last recorded. Expect one extra sign-in, because the saved token belonged to the registration that was replaced.

   If a different port does not help, the store itself can be cleared: it lives at `~/.mcp-auth`, or wherever `MCP_REMOTE_CONFIG_DIR` points. Removing it makes every server you reach through this proxy sign in again, so prefer the port change above, and never delete it to work around a port conflict you have not confirmed.

   None of this is a permanent fix. The failure returns if the host exits without shutting the proxy down, leaving an orphaned proxy still running and holding the port. When that happens you do not need this block at all: find the orphan with `lsof -nP -iTCP:<port> -sTCP:LISTEN`, or `netstat -ano | findstr :<port>` on Windows, and stop it. A second proxy started while the first is still running normally waits for it, but only while the first one's lock is under 30 minutes old; past that the wait is skipped and the crash returns. On Windows the proxy never waits at all. The durable fix is proposed upstream but not yet merged, in [mcp-remote PR #262](https://github.com/geelen/mcp-remote/pull/262).

   </details>

4. Restart the host.
5. Refresh the plugin or Power source so you get the current recipe, if you installed from one: `claude plugin marketplace update outsystems` (Claude Code), or update the Power from Kiro's Powers panel (`git pull` in your clone if you installed from a local registry file). Reinstalling from a stale source re-applies the old setup command.
6. Reinstall from the recipe above.

### Getting logs

Attach these when opening an issue; they are what makes a report actionable.

- **Claude Code**: `claude mcp list` output, plus `claude --debug` for a failing session.
- **Claude Desktop**: `~/Library/Application Support/Claude/logs/` on macOS, `%APPDATA%\Claude\logs\` on Windows, `~/.config/Claude/logs/` on Linux. There is a per-server log file alongside the main one.
- **VS Code**: the MCP server output channel, via `MCP: List Servers` then **Show Output**.
- **Kiro**: the Powers and MCP output channels.

Redact your tenant hostname and any bearer tokens before posting.
