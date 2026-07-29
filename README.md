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
Step 4: when I tell you, run `claude mcp add -s user --transport http --client-id service_studio --callback-port 7890 outsystems https://<my-tenant>/mcp` (substitute my actual tenant for `<my-tenant>`).
Step 5: tell me to restart Claude Code, then ask anything OutSystems-related; you'll drive the OAuth flow automatically via Claude Code's synthesized `authenticate` tool (a client convenience, not a server tool). Do NOT tell me to run `/mcp -> outsystems -> Authenticate` manually.
```

After install, you can also type `/outsystems-feedback <message>` in Claude Code to send feedback about the agent experience so the maintainers can act on it. The slash command is Claude-Code-only (and uses the `outsystems-` prefix so it doesn't collide with Claude Code's built-in `/feedback`, which routes to Anthropic's issue tracker); on other harnesses, ask the agent in plain language ("send a thumbs-up about the OutSystems agent") and it will invoke the underlying `submit_feedback` MCP tool.

## Install - Claude Desktop

Paste into Claude Desktop (requires Node.js with `npx` available on your machine):

```
Install the OutSystems MCP server in Claude Desktop.
Step 1: install `mcp-remote` globally: `npm install -g mcp-remote`. This is idempotent — safe to run even if already installed.
Step 2: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 3: locate the Claude Desktop config file — macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows: `%APPDATA%\Claude\claude_desktop_config.json`. Read the file (start from `{}` if it doesn't exist). Preserve every existing key. Patch the top-level `mcpServers` object by adding or replacing the `outsystems` entry:
  - macOS/Linux: `{"command": "npx", "args": ["mcp-remote", "https://<my-tenant>/mcp"]}`
  - Windows: `{"command": "cmd", "args": ["/c", "npx mcp-remote https://<my-tenant>/mcp"]}`
Substitute my actual tenant hostname for `<my-tenant>`. Write the file back.
Step 4: tell me to restart Claude Desktop. After restarting, the first OutSystems tool call will open a browser window for OAuth sign-in — complete the sign-in when prompted.
```

> **Note:** Claude Desktop launches processes with a minimal PATH, so `npx` may not be found even if it works in your terminal. If the server fails to connect after restart, find the full path to `npx` (run `which npx` on macOS/Linux or `where npx` on Windows) and replace `"npx"` in the config with that full path (e.g. `/opt/homebrew/bin/npx`).

## Install - Kiro Chat

Paste into Kiro Chat:

```
Install the OutSystems Power from https://github.com/OutSystems/outsystems-mcp.
Step 1: clone the repo to ~/git/outsystems-mcp if it isn't there yet: `git clone https://github.com/OutSystems/outsystems-mcp.git ~/git/outsystems-mcp`.
Step 2: base64-encode ~/git/outsystems-mcp/kiro/outsystems/icon.png with `base64 -w0` (Linux) or `base64 -i` (macOS). Then write ~/.kiro/powers/registries/outsystems.json with this content (substitute the literal value of $HOME, and inline the base64 string in place of <ICON_BASE64>):
{"name":"OutSystems","type":"local","powers":[{"name":"outsystems","displayName":"OutSystems - MCP","description":"Edit, publish, deploy OutSystems apps from your AI assistant.","iconUrl":"data:image/png;base64,<ICON_BASE64>","source":{"type":"local","path":"$HOME/git/outsystems-mcp/kiro/outsystems"},"autoInstall":true}]}
Step 3: tell me to restart Kiro so it auto-installs the Power.
Step 4: after the restart, ask me for my OutSystems tenant hostname.
Step 5: when I tell you, set the URL `https://<my-tenant>/mcp` in ~/.kiro/settings/mcp.json under top-level `mcpServers.outsystems` (read first, preserve every other entry): `{"type": "http", "url": "https://<my-tenant>/mcp", "timeout": 100000}`.
Step 6: tell me the OAuth sign-in opens automatically on the next OutSystems tool call — Kiro runs the flow itself and opens the browser for the localhost callback; I just complete the sign-in when prompted. There is no `authenticate` tool to call in Kiro.
```

## Install - Copilot in VS Code

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

Paste into VS Code copilot chat:

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

## Install - M365 Copilot (web browser)

Currently, this assistant does not support custom MCP servers.

## Install - other AI assistants (best effort)

For other agentic harnesses (Codex CLI, Cursor, Continue, Cline, Aider, etc.), this is a best-effort install path — the MCP server is a stock streamable-HTTP MCP endpoint with OAuth + Dynamic Client Registration, so most harnesses should be able to wire it up, but we don't validate the flow ourselves. If something breaks, file an issue with the symptoms.

Paste into your harness:

```
Install the OutSystems MCP server.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: register `outsystems` as an MCP server in this harness's configuration, pointing at `https://<my-tenant>/mcp` over the streamable HTTP transport. Use whatever wiring the harness prefers — a CLI command (similar to Claude Code's `claude mcp add`), a settings UI, or hand-editing the harness's MCP config file. The server requires OAuth and supports Dynamic Client Registration, so no shared `client_id` setup is needed.
Step 3: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/SKILL.md and inject its contents into this harness's instructions/rules/system-prompt mechanism (e.g. `AGENTS.md` for Codex CLI, `.cursorrules` for Cursor, the system prompt config for Continue, etc.). The skill covers conventions (OML stays server-side, polling shape for long-running tools, error category enums, mentor session round-trip) that the tool descriptions alone don't fully convey.
Step 4: trigger authentication. If the harness synthesizes per-server `authenticate` / `complete_authentication` tools after registration (as Claude Code does — they're a client convenience, not server tools), call those (lazy on first tool call). Otherwise let the harness's built-in MCP auth UI handle the OAuth handshake.
Step 5: depending on the harness, the new MCP server may not be visible until you reload its MCP config or restart. If the harness has a CLI to list registered MCP servers (similar to `claude mcp list`), run it to check whether `outsystems` is visible — if not, tell me to restart the harness. Once the tools appear, ask me anything OutSystems-related to confirm the install is complete.
```
