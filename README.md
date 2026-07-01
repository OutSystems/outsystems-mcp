# outsystems-mcp

Distribution repo for the OutSystems MCP: Claude Code plugin, Claude Desktop, and Kiro Power. To install, paste the matching prompt below into your AI assistant.

## ⚠️ Disclaimer
> Early Alpha. Please Read Before Using
> This project is in early alpha and is provided as-is, without warranties or guarantees of any kind. It is not production-ready, expect bugs, incomplete features, breaking changes, and unstable behaviors. Do not rely on it for critical, commercial, or production use.
> No support, SLAs, or maintenance commitments are offered. We are sharing this publicly because we value community input, not because it is ready for broad adoption.
> Bug reports, feature requests, and feedback are welcome, feel free to open an issue. Responses and fixes happen on a best-effort basis with no defined timeline.

## Before you install

Some installs get stuck on an older plugin version (0.6.0 / 0.6.2) even with autoupdate enabled, which silently keeps you on a pre-fix install prompt. Before pasting any install prompt below:

- **Claude Code / Claude Desktop:** open Settings > Extensions (or Plugins), find `outsystems`, and click "Check for updates". Confirm the version is at least the current release. If you cannot see or click update, follow the Reset in Troubleshooting.
- **Kiro:** run `git pull` in the local `outsystems-mcp` clone before restarting Kiro.

## Install - Claude Code

Paste into Claude Code:

```
Install the OutSystems outsystems-mcp plugin from OutSystems/outsystems-mcp on GitHub.
Step 1: run `claude plugin marketplace add OutSystems/outsystems-mcp`.
Step 2: run `claude plugin install outsystems@outsystems`.
Step 3: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 4: when I tell you, run `claude mcp add -s user --transport http --client-id service_studio --callback-port 7890 outsystems https://<my-tenant>/mcp` (substitute my actual tenant for `<my-tenant>`).
Step 5: tell me to restart Claude Code, then ask anything OutSystems-related; the OAuth flow is normally driven automatically by Claude Code's synthesized `authenticate` tool (a client convenience, not a server tool). If the auto-auth does not trigger, tell me to open `/mcp`, select `outsystems`, and click Authenticate.
```

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

## Install - other AI assistants (best effort)

Claude Code and Kiro Chat are the two harnesses we test against. For other agentic harnesses (Codex CLI, Cursor, Continue, Cline, Aider, etc.), this is a best-effort install path — the MCP server is a stock streamable-HTTP MCP endpoint with OAuth + Dynamic Client Registration, so most harnesses should be able to wire it up, but we don't validate the flow ourselves. If something breaks, file an issue with the symptoms.

Paste into your harness:

```
Install the OutSystems MCP server.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: register `outsystems` as an MCP server in this harness's configuration, pointing at `https://<my-tenant>/mcp` over the streamable HTTP transport. Use whatever wiring the harness prefers — a CLI command (similar to Claude Code's `claude mcp add`), a settings UI, or hand-editing the harness's MCP config file. The server requires OAuth and supports Dynamic Client Registration, so no shared `client_id` setup is needed.
Step 3: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/SKILL.md and inject its contents into this harness's instructions/rules/system-prompt mechanism (e.g. `AGENTS.md` for Codex CLI, `.cursorrules` for Cursor, the system prompt config for Continue, etc.). The skill covers conventions (OML stays server-side, polling shape for long-running tools, error category enums, mentor session round-trip) that the tool descriptions alone don't fully convey.
Step 4: trigger authentication. If the harness synthesizes per-server `authenticate` / `complete_authentication` tools after registration (as Claude Code does — they're a client convenience, not server tools), call those (lazy on first tool call). Otherwise let the harness's built-in MCP auth UI handle the OAuth handshake.
Step 5: depending on the harness, the new MCP server may not be visible until you reload its MCP config or restart. If the harness has a CLI to list registered MCP servers (similar to `claude mcp list`), run it to check whether `outsystems` is visible — if not, tell me to restart the harness. Once the tools appear, ask me anything OutSystems-related to confirm the install is complete.
```

## Troubleshooting

If the install prompt succeeded but the MCP is still not working, match the symptom below.

### "The authenticate tool isn't loaded, authenticate via the Claude CLI"

Your plugin is still on an older version that used the pre-fix install prompt. Update it (see "Before you install") and re-run the install prompt in a fresh Claude Code tab. If updating does not stick, follow the Reset below.

### "This session is non-interactive, I can't run the OAuth flow here"

Same underlying cause as above (older install prompt still cached). Update the plugin, then Reset if needed.

### "Server Disconnected" or "failed authorization" in Developer Settings

The OAuth sign-in did not complete inside Claude Desktop's server-initialization timeout. Complete OAuth from a terminal, where there is no timeout:

```
npx -y mcp-remote https://<my-tenant>/mcp
```

Sign in when the browser opens. Once the terminal reports the token was saved (a file appears under `~/.mcp-auth/` on macOS/Linux or `%USERPROFILE%\.mcp-auth\` on Windows), press Ctrl+C and restart Claude Desktop. Subsequent launches reuse the cached token.

### Windows: `npx` not found by Claude Desktop

Claude Desktop launches processes with a minimal PATH. Run `where npx` in a terminal, then edit `claude_desktop_config.json` and replace `"npx"` with the full path returned.

### Reset (when updates will not stick)

1. Uninstall the `outsystems` plugin.
2. In Claude, open Help > Troubleshooting > Clear cache.
3. Fully quit and reopen Claude.
4. Reinstall the plugin from the marketplace. This pulls the latest version.
5. Paste the install prompt again in a fresh Claude Code tab.

## Getting logs

If you need to file a bug or ask for help, attach the relevant bridge log:

- **macOS:** `~/Library/Logs/Claude/mcp-server-outsystems.log`
- **Windows:** `%APPDATA%\Claude\logs\mcp-server-outsystems.log`
- **Linux:** `~/.config/Claude/logs/mcp-server-outsystems.log`

The file is per-server. Replace `outsystems` with the key name you used in `claude_desktop_config.json`.
