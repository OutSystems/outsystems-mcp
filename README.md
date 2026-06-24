# outsystems-mcp

Distribution repo for the OutSystems MCP: Claude Code plugin + Kiro Power. To install, paste the matching prompt below into your AI assistant.

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
