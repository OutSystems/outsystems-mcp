# outsystems-mcp

Distribution repo for the OutSystems MCP. To install, paste the matching prompt below into your AI assistant.

Every harness section below sets up two artifacts and says how to keep the skill current. Your agent needs both: the MCP server without the skill gives it every tool and none of the rules, the confirm-before-destructive rule included, and the skill without the MCP server leaves it nothing to call. Some hosts deliver both in one step; the section says so when that is the case. The latest published skill is the one on the `main` branch of this repo; there are no release notes, so the [commit history](https://github.com/OutSystems/outsystems-mcp/commits/main) is where changes show up.

- **Skill**: the document that tells the agent how to work with OutSystems: confirm before changing tenant state, poll long-running operations until they finish, decide retries from the error category, prefer the asset key over names. It changes with new releases, so each section carries an **Update** step. Some hosts wrap it in a plugin or a Power.
- **MCP server**: the OutSystems endpoint at `https://<my-tenant>/mcp`, which exposes the tools and signs you in to your tenant. OutSystems hosts it and updates it on the tenant side, and your harness only stores its URL; if you reach it through the `mcp-remote` local proxy, as the Claude Desktop install does, also keep `mcp-remote` at 0.14.0 or later (see [Install - Claude Desktop](#install---claude-desktop)).

## Install - Claude Code

**Skill and MCP server:** one plugin install delivers both. The plugin carries the skill and declares the MCP server from your tenant hostname. Paste into Claude Code:

```
Install the OutSystems outsystems-mcp plugin from OutSystems/outsystems-mcp on GitHub.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`). Strip any scheme, leading `www.`, trailing slash, and path or query, keeping only the host. If the result doesn't match `^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$`, ask again rather than proceeding with an unvalidated value: the next step does not validate it, and a value carrying a scheme prefix or a path produces a server URL that cannot resolve.
Step 2: run `claude plugin marketplace add OutSystems/outsystems-mcp`.
Step 3: run `claude plugin install outsystems@outsystems --config tenant_hostname=<my-tenant>`, where `<my-tenant>` is exactly the bare hostname from Step 1. The plugin declares the MCP server itself, at `https://<my-tenant>/mcp`, so there is no separate `claude mcp add` step. If `claude` rejects `--config`, my Claude Code predates plugin options: tell me to update Claude Code and re-run this step; if updating is not possible, install without `--config` and tell me to run `/plugin configure outsystems@outsystems` and type that same bare hostname there. Never add a `--client-id` or pin a callback port anywhere: the server supports OAuth Dynamic Client Registration, so Claude Code registers its own client on an ephemeral loopback port.
Step 4: run `claude mcp list`. Expect either `plugin:outsystems:outsystems: https://<my-tenant>/mcp`, or, if I installed before 0.20.0, only `outsystems: https://<my-tenant>/mcp`: that is an older entry hiding the plugin's server as a duplicate. In the second case, or if both appear with different URLs, run `claude mcp get outsystems` to read its `Scope` and `URL`, tell me both, and, unless that scope is `project` (shared config: report it and let me decide), ask before running `claude mcp remove outsystems -s <that scope>`; then re-run `claude mcp list` and confirm `plugin:outsystems:outsystems` now appears. If the list shows no `outsystems` line at all, the tenant option was not stored: re-run Step 3.
Step 5: tell me to restart Claude Code, then ask anything OutSystems-related; you'll drive the OAuth flow automatically via Claude Code's synthesized `authenticate` tool (a client convenience, not a server tool). If that doesn't trigger, or a call fails with an auth error, tell me to open `/mcp`, pick the `outsystems` server marked as coming from the plugin, and choose Authenticate as the fallback.
```

**Update:** run `claude plugin marketplace update outsystems`, then `claude plugin update outsystems@outsystems`, then restart Claude Code. The first command refreshes Claude Code's cached copy of this repo's marketplace; the second compares the installed plugin version with it and installs the newer plugin, or reports `already at the latest version`. Run both, in this order: the second alone compares against the stale cache and reports the old version as the latest, and the first alone leaves the installed plugin as it was. The update refreshes the skill however the MCP server is registered, including an older `claude mcp add` entry.

Upgrading from a version before 0.20.0? The old recipe registered the server with `claude mcp add` at user scope. That entry keeps working, and when it points at the same tenant Claude Code keeps it and hides the plugin's server as a duplicate. To move to the plugin's server: set the option with `claude plugin install outsystems@outsystems --config tenant_hostname=<my-tenant>` (bare hostname, no scheme prefix, no path; on an installed plugin this only updates the option), remove the old entry with `claude mcp remove outsystems -s user`, and restart Claude Code. Removing the entry also drops its saved sign-in, so expect one sign-in on your next OutSystems request. The plugin's tools are named `mcp__plugin_outsystems_outsystems__<tool>`, so rename any permission rules or hooks you wrote against `mcp__outsystems__<tool>`.

After install, you can also type `/outsystems-feedback <message>` in Claude Code to send feedback about the agent experience so the maintainers can act on it. The slash command is Claude-Code-only (and uses the `outsystems-` prefix so it doesn't collide with Claude Code's built-in `/feedback`, which routes to Anthropic's issue tracker); on other harnesses, ask the agent in plain language ("send a thumbs-up about the OutSystems agent") and it will invoke the underlying feedback tool.

## Install - Claude Desktop

Use the local proxy below. Claude Desktop's native **Add custom connector** flow always fails during OAuth sign-in against any OutSystems tenant: the connector's `claude.ai` callback URL is rejected, because the tenant's identity provider accepts only loopback redirect URIs. It is not a working install path; the native steps are kept in the collapsed section below for reference only.

**MCP server:** paste into Claude Desktop (requires Node.js with `npx` available on your machine):

```
Install the OutSystems MCP server in Claude Desktop via a local proxy.
Step 1: confirm Node.js is available (`npx --version`). If it isn't, stop and tell me to install Node.js first — writing the config below without it produces a server that silently fails to connect. Then install or upgrade `mcp-remote` globally: `npm install -g mcp-remote@latest` (idempotent, safe if already installed). The proxy must be 0.14.0 or later: releases 0.9.0 through 0.13.5 fail every sign-in with `IssuerMismatchError`.
Step 2: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`). Strip any scheme, leading `www.`, trailing slash, and path or query, keeping only the host. If the result doesn't match `^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$`, ask again rather than proceeding with an unvalidated value.
Step 3: locate the Claude Desktop config file, `claude_desktop_config.json`: on macOS it is in `Library/Application Support/Claude` under my home folder, on Windows in the `Claude` folder of my roaming AppData directory, on Linux in `.config/Claude` under my home folder. Read the file (start from `{}` if it doesn't exist). Preserve every existing key — other entries belong to other MCP servers and may hold private values, so don't paste the full file contents back to me; quote only the `outsystems` entry you're adding or changing. Patch the top-level `mcpServers` object by adding or replacing the `outsystems` entry:
  - macOS/Linux: `{"command": "npx", "args": ["mcp-remote", "https://<my-tenant>/mcp"]}`
  - Windows: `{"command": "cmd", "args": ["/c", "npx mcp-remote https://<my-tenant>/mcp"]}` (safe here because Step 2 already restricted the tenant hostname to the pattern above, so it can't break out of this shell string)
Substitute my actual tenant hostname for `<my-tenant>`. Write the file back.
Step 4: tell me to restart Claude Desktop.
Step 5: After restarting, if the server fails to connect: Claude Desktop launches processes with a minimal PATH, and a broken, stale, or mistyped `"command"` value looks identical to Desktop. macOS/Linux, replace whatever the `"command"` value currently is with the full path from `which npx`. Windows, if the `"command"` value is anything other than `"cmd"`, restore it to `"cmd"` first; then replace whatever text stands in for `npx` inside the `/c` argument string with the `.cmd` path from `where npx` (the line ending in `.cmd`), quoting it if it contains a space — it commonly does (e.g. `C:\Program Files\nodejs\npx.cmd`). Restart Claude Desktop again and retry; if it still doesn't connect after that, stop and point me at https://github.com/OutSystems/outsystems-mcp#troubleshooting rather than continuing to guess. Otherwise, the first OutSystems tool call will open a browser window for OAuth sign-in; complete the sign-in when prompted.
```

**Skill:** once the MCP server is wired up above, install the plugin too: it delivers the skill.

> **Requires a paid plan:** Plugins require a paid plan (Pro, Max, Team, Enterprise), and Enterprise admins may restrict which plugins install.

Add the `OutSystems/outsystems-mcp` marketplace and install the `outsystems` plugin from Claude Desktop's plugin install flow, the same marketplace and plugin the Claude Code recipe above uses, then restart Claude Desktop.

The plugin also declares the same server for Claude Code, built from a `tenant_hostname` plugin option. Desktop's Chat tab keeps using the local-proxy entry you just wrote, and the Code tab loads that same entry from `claude_desktop_config.json`, so both work with the option unset. We have not verified whether Desktop asks for the option when you install the plugin, nor whether it loads the plugin's server at all. Set the option only if you also want the plugin's own HTTP server; if the Code tab does load it, expect two `outsystems` servers there. Setting it needs the standalone `claude` CLI in a terminal: `claude plugin install outsystems@outsystems --config tenant_hostname=<my-tenant>` (bare hostname, no scheme prefix, no path).

<details>
<summary>Native "Add custom connector" steps (not currently working, kept for reference)</summary>

1. Open **Settings > Connectors**.
2. Click **Add custom connector**.
3. Enter `https://<my-tenant>/mcp`, substituting your OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
4. Click **Add**. The first OutSystems tool call opens a browser for OAuth sign-in, which always fails against any OutSystems tenant today; use the local-proxy steps above instead.

Available on Free, Pro, Max, Team and Enterprise, with Free limited to one custom connector. A custom connector is also reached from Anthropic's cloud rather than from your machine, so it cannot reach a tenant that is VPN-only or IP-allowlisted; the local proxy is required there too.

If the flow starts working: on a Team or Enterprise plan you may not see "Add custom connector" at all, because adding custom connectors is an organization-level permission. An Owner adds the connector in **Admin settings > Connectors** and members then click **Connect** on it. If your organization has custom connectors disabled entirely, no member can add one and neither can an Owner without changing that policy.

</details>

> **Note:** the plugin installed above delivers the same OutSystems skill Claude Code gets, including the confirm-before-destructive rule, once both the local proxy and the plugin are set up. Plugins require a paid plan, so on Free the gap remains: read [SKILL.md](SKILL.md) if you want the skill's rules, and expect to confirm destructive operations yourself rather than being prompted.

**Update:** uninstall the `outsystems` plugin, then reinstall it from the same marketplace through Claude Desktop's plugin install flow, and restart Claude Desktop. Whether Desktop picks up a new plugin version in place is unverified, so reinstalling is the dependable path; if the reinstall still shows the old version, remove and re-add the `OutSystems/outsystems-mcp` marketplace first. The MCP server entry in `claude_desktop_config.json` needs no update. On Free, re-read [SKILL.md](SKILL.md) on `main` for the current rules.

## Install - Kiro Chat

**Skill:** the OutSystems Power carries it. Install the Power yourself from the Powers panel: **Add Custom Power** > **Import power from GitHub**, paste the URL below, then **Install**.

```
https://github.com/OutSystems/outsystems-mcp/tree/main/kiro/outsystems
```

The Power uses Kiro's Agent Plugins format: `plugin.json` declares it and `skills/outsystems/SKILL.md` is the skill.

**MCP server:** then paste into Kiro Chat:

```
Finish setting up the OutSystems Power in Kiro.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: when I tell you, set the URL `https://<my-tenant>/mcp` in ~/.kiro/settings/mcp.json under top-level `mcpServers.outsystems` (read first, preserve every other entry): `{"type": "http", "url": "https://<my-tenant>/mcp"}`.
Step 3: tell me the OAuth sign-in opens automatically on the next OutSystems tool call. Kiro runs the flow itself and opens the browser for the localhost callback; I just complete the sign-in when prompted. There is no `authenticate` tool to call in Kiro.
```

The tenant URL goes under the **top-level** `mcpServers`, not under `powers.mcpServers`. Kiro rewrites the whole `powers` block on every Power install, uninstall or update, so a URL stored there is lost on the next update; a URL at the top level is untouched.

**Status watcher (optional):** a long Mentor turn or publish makes the assistant check its status many times, and each check re-reads the whole conversation. The status watcher is a small agent that does that waiting on a cheaper model, in a context of its own, and can do nothing but read the status and pause. A Power can't ship an agent, so add it to each workspace where you build with OutSystems. Paste into Kiro Chat from that workspace:

```
Add the OutSystems status watcher to this workspace.
Step 1: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/kiro/agents/status-watcher.json and save its exact bytes to `.kiro/agents/status-watcher.json` in my workspace root, creating the folder if needed. If that file already exists, overwrite it only if its `name` field is `status-watcher`; otherwise stop and tell me.
Step 2: don't change the file: its `tools` list, and the `shell` setting that allows only `sleep`, are what keep the watcher read-only.
Step 3: tell me to start a new chat session so Kiro loads the agent.
```

To update it, run the same recipe again. To remove it, delete `.kiro/agents/status-watcher.json`; the assistant then checks the status itself, as it does without the file. Verified in Kiro CLI 2.26; the Kiro IDE reads the same `.kiro/agents` folder, but the watcher has not been run there.

**Update:** update the OutSystems Power from the Powers panel, or, if the panel offers no update, uninstall it and import it again from the same URL. If you installed through the registry file below, run `git pull` in `~/git/outsystems-mcp` instead; Kiro watches that directory. The MCP server URL stays in place either way, because it lives at the top level. Whether Kiro compares the Power's version on update is unverified, so afterwards compare the `version` in `~/.kiro/powers/installed/outsystems/plugin.json` with the one in [`kiro/outsystems/plugin.json`](kiro/outsystems/plugin.json) on `main`; if they differ, uninstall and import again.

<details>
<summary>Alternative: install via a registry file (adds the icon to the Powers list)</summary>

The GitHub import registers the Power without an icon. If you want the OutSystems logo (the PNG image in the kiro/outsystems folder of the clone) in the Powers list, register it yourself instead. Paste into Kiro Chat:

```
Install the OutSystems Power from https://github.com/OutSystems/outsystems-mcp.
Step 1: clone the repo to ~/git/outsystems-mcp if it isn't there yet: `git clone https://github.com/OutSystems/outsystems-mcp.git ~/git/outsystems-mcp`.
Step 2: the folder ~/git/outsystems-mcp/kiro/outsystems contains exactly one PNG image, the OutSystems logo. List that folder to find it, then base64-encode that file with `base64 -w0` (Linux) or `base64 -i` (macOS). Then write ~/.kiro/powers/registries/outsystems.json with this content (substitute the literal value of $HOME, and inline the base64 string in place of <ICON_BASE64>):
{"name":"OutSystems","type":"local","powers":[{"name":"outsystems","displayName":"OutSystems - MCP","description":"Edit, publish, deploy OutSystems apps from your AI assistant.","iconUrl":"data:image/png;base64,<ICON_BASE64>","source":{"type":"local","path":"$HOME/git/outsystems-mcp/kiro/outsystems"},"autoInstall":true}]}
Step 3: Kiro watches that directory and installs the Power within a few seconds. Restart only if it doesn't appear.
Step 4: then complete Steps 1 to 3 of the main recipe above to set the tenant URL.
```

The icon has to be inlined as base64 because Kiro's Powers view only loads images from `data:` URIs or its own CDN, so a `raw.githubusercontent.com` URL will not render.

</details>

## Install - Copilot in VS Code

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

**MCP server:** one-click: [**Add the OutSystems MCP server to VS Code**](https://vscode.dev/redirect/mcp/install?name=outsystems&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2F%24%7Binput%3Aos_tenant%7D%2Fmcp%22%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22os_tenant%22%2C%22description%22%3A%22Your%20OutSystems%20tenant%20hostname%20%28e.g.%20mycompany.outsystems.dev%29%22%7D%5D). VS Code prompts you for your tenant hostname the first time the server starts and remembers it after that. Or use Step 2 of the prompt below.

**Skill:** Step 3 of the prompt below copies it into your workspace. The one-click link installs only the MCP server, so run Step 3 afterwards if you used it.

Paste into VS Code copilot chat:

```
Install the OutSystems MCP server in VS Code Copilot.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: open my user MCP config (behind `MCP: Open User Configuration`) or create `.vscode/mcp.json`. Read it first and preserve existing entries, then add under the top-level `servers` object (the key is `servers`, NOT `mcpServers`) the canonical `servers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json), substituting my tenant for `<my-tenant>`:
{"outsystems": {"type": "http", "url": "https://<my-tenant>/mcp"}}
Do NOT add an `oauth.clientId` — the server supports Dynamic Client Registration and VS Code registers its own client automatically.
Step 3: install the OutSystems skill: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes to `.github/copilot-instructions.md` in my workspace. Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file already exists do NOT hand-merge; save the copy alongside it and tell me.
Step 4: tell me to open the MCP config I edited (either `.vscode/mcp.json` or the user configuration behind `MCP: Open User Configuration`), check for `outsystems` under `servers`, and start it. A browser opens automatically for OAuth on first connection.
Step 5: then tell me to ask `list 10 of my outsystems apps` to ensure it is working
```

**Update:** the skill is a copy of the file on `main` and never refreshes itself. Paste into VS Code copilot chat:

```
Update the OutSystems skill in my workspace.
Fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes over `.github/copilot-instructions.md`, but only if that file's first line is `# OutSystems - Remote MCP`, which marks an earlier copy of the skill. If the first line is anything else, or the file is missing, write nothing and tell me what you found; if an earlier install saved the copy alongside an existing file, tell me its path. Copy it verbatim: do NOT retype or summarize the contents (that truncates the file and corrupts escaping).
```

## Install - Copilot in CLI

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

**MCP server:** Step 2 of the prompt below registers it.

**Skill:** Step 3 of the prompt below copies it into your working directory.

Paste into copilot:

```
Install the OutSystems MCP server in Copilot CLI.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: run `copilot mcp add --transport http outsystems https://<my-tenant>/mcp` (substitute my tenant). This writes the server to `~/.copilot/mcp-config.json` under the top-level `mcpServers` object — it's added to config, but a CLI session that's already running won't load it until Step 4. This matches the canonical `mcpServers.outsystems` block at https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json. Add no auth headers or client_id; the server uses OAuth + Dynamic Client Registration.
Step 3: install the OutSystems skill: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes to `.github/copilot-instructions.md` in the working directory — that is the path Copilot reads, so default to it. Use `AGENTS.md` instead only when the project already keeps its own conventions there; an `AGENTS.md` that holds an OutSystems skill installed for a different assistant (Cursor's recipe writes one) is not the project's own file, so in that case write `.github/copilot-instructions.md` and tell me. Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file already exists do NOT hand-merge; save the copy alongside it and tell me.
Step 4: since `copilot mcp add` wrote the server to config from outside this running session, the session hasn't loaded it yet. Tell me to type `/mcp reload` in the CLI to load it (then optionally `/mcp show outsystems` to confirm it's listed). Note: `/mcp ...` are interactive slash commands I type in the REPL — you cannot run them for me, so ask me to run them rather than executing them yourself. The OAuth flow runs on the first OutSystems tool call — a browser opens for me to authorize.
Step 5: once the tools are listed, tell me to ask `list 10 of my outsystems apps` to ensure it is working.
````

**Update:** the skill is a copy of the file on `main` and never refreshes itself. Paste into copilot:

```
Update the OutSystems skill in the working directory.
Find the copy an earlier install wrote: `.github/copilot-instructions.md`, or `AGENTS.md` if that is where it went; if an earlier install saved the copy alongside an existing file, tell me its path. It is the file whose first line is `# OutSystems - Remote MCP`. Fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md and save its exact bytes over that file. If no candidate file starts with that line, write nothing and tell me what you found. Copy it verbatim: do NOT retype or summarize the contents (that truncates the file and corrupts escaping).
```

## Install - Copilot in Visual Studio (Windows)

> On a Copilot Business/Enterprise plan, an admin must enable the "MCP servers in Copilot" policy.

**MCP server:** Step 2 of the prompt below registers it.

**Skill:** Step 3 of the prompt below downloads it into your solution.

Paste into copilot chat:

```
Install the OutSystems MCP server in Visual Studio Copilot.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: create or edit `.mcp.json` in my solution dir (`<SolutionDir>\.mcp.json`) or global `%USERPROFILE%\.mcp.json`. Read it first and preserve existing entries, then add under the top-level `servers` object the canonical `servers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/mcp.json), substituting my tenant:
{"outsystems": {"type": "http", "url": "https://<my-tenant>/mcp"}}
Do NOT add an `oauth.clientId` — the server supports Dynamic Client Registration.
Step 3: install the OutSystems skill by DOWNLOADING it — do NOT read it into chat and retype it. Run this terminal command from the repo root (approve it when Visual Studio asks): `New-Item -ItemType Directory -Force .github | Out-Null; Invoke-WebRequest -Uri https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md -OutFile .github\copilot-instructions.md`. Then verify it downloaded fully: `Select-String -Path .github\copilot-instructions.md -Pattern '^## Feedback' -Quiet` should print `True`, because `## Feedback` is the file's last section; if it prints `False`, re-run the command, never hand-type the content.
Step 4: tell me to open the Tools picker, and ENABLE the `outsystems` tools — in Visual Studio, MCP tools are disabled by default and must be turned on manually. It will fail due to authentication, click "view details" and follow the steps in the authentication section. Finally, enable all tools.
Step 5: tell me to ask `list 10 of my outsystems apps` to ensure it is working.
```

**Update:** the skill is a copy of the file on `main` and never refreshes itself. Paste into copilot chat:

```
Update the OutSystems skill in my solution by DOWNLOADING it again: do NOT read it into chat and retype it.
First check that `.github\copilot-instructions.md` is an earlier copy of the skill: `Get-Content .github\copilot-instructions.md -TotalCount 1` should print `# OutSystems - Remote MCP`. If it prints anything else, or the file is missing, stop and tell me.
Then run from the repo root (approve it when Visual Studio asks): `Invoke-WebRequest -Uri https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/copilot/skill.md -OutFile .github\copilot-instructions.md`.
Verify: `Select-String -Path .github\copilot-instructions.md -Pattern '^## Feedback' -Quiet` should print `True`; if it prints `False`, re-run the download.
```

## Install - Cursor CLI (all plans, individual accounts included)

No plugin and no team admin needed — this path works on a personal/individual Cursor account as well as on Team/Enterprise.

**MCP server:** Step 2 of the prompt below registers it.

**Skill:** Step 3 of the prompt below copies it into your workspace.

Paste into Cursor agent:

```
Install the OutSystems MCP server in Cursor CLI.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: create or edit `~/.cursor/mcp.json` (global config) or `.cursor/mcp.json` (project config). Cursor merges both files, and on a server-name collision the project entry is the one that wins. Read it first and preserve existing entries, then add under the top-level `mcpServers` object (NOT `servers`) the canonical `mcpServers.outsystems` block (source: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/mcp.json), substituting my tenant for `<my-tenant>`:
{"outsystems": {"url": "https://<my-tenant>/mcp"}}
Important: use `mcpServers` as the key (not `servers`), and omit `type` — Cursor infers the transport from the `url`. Never set `"type": "streamable-http"`; that value makes Cursor CLI silently drop the entire `mcp.json`.
Only touch Cursor's own config. Do NOT read, copy from, or migrate any other assistant's MCP config — `.vscode/mcp.json`, `.mcp.json`, `~/.copilot/mcp-config.json`, `~/.claude.json`, `claude_desktop_config.json`, `~/.kiro/settings/mcp.json`, `~/.gemini/settings.json`, `.continue/`, or any other assistant's file — even if one exists and already has an `outsystems` entry; different keys and schemas mean a block lifted from one silently never loads in Cursor. Ask me for the tenant instead of hunting for it. Between the two Cursor configs, prefer the project one when my workspace already has it.
Step 3: install the OutSystems skill: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/skills/outsystems/SKILL.md and save its exact bytes to `AGENTS.md` in my workspace root — Cursor loads that file verbatim. Do NOT save it under `.cursor/rules/`: that loader only reads `.mdc` files carrying rule frontmatter, so a plain `.md` copy there never loads. If `AGENTS.md` already exists, read it before writing: when it already holds an OutSystems skill that another assistant's setup put there, stop and tell me — that file is already doing this job and a second copy alongside it helps nobody. Copy it verbatim — do NOT retype or summarize the contents (that truncates the file and corrupts escaping), and if the file exists with unrelated content do NOT hand-merge; save the copy alongside it and tell me.
Step 4: in a terminal, run: `agent mcp list` (verify outsystems appears), then `agent mcp enable outsystems` if it shows "needs approval", then `agent mcp login outsystems` (opens browser for OAuth sign-in; complete it there).
Step 5: once logged in, ask `list 10 of my outsystems apps` to ensure it is working.
```

**Update:** the skill is a copy of the file on `main` and never refreshes itself; plugin version bumps reach only the Cursor App path. Paste into Cursor agent:

```
Update the OutSystems skill in my workspace.
Check that `AGENTS.md` in my workspace root is an earlier copy of the skill: it starts with a frontmatter block carrying `name: outsystems`, followed by the heading `# OutSystems - Remote MCP`. If it doesn't, or the file is missing, write nothing and tell me what you found; if an earlier install saved the copy alongside an existing file, tell me its path. Otherwise fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/skills/outsystems/SKILL.md and save its exact bytes over `AGENTS.md`. Copy it verbatim: do NOT retype or summarize the contents (that truncates the file and corrupts escaping).
```

## Install - Cursor App (Plugin)

> **Team/Enterprise plans only:** Requires team admin to import plugin to Team Marketplace.

**Skill and MCP server:** the plugin delivers the skill, and on first use the agent writes the MCP server entry to your personal `~/.cursor/mcp.json`, so there is no separate MCP server step.

**Team Admin:** Import the plugin to your Marketplace:
1. Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → **Import from Repo**
2. Enter: `https://github.com/OutSystems/outsystems-mcp`
3. Review the `outsystems` plugin and save it as **Required** — or at minimum **Default On**.

> Save it as **Required** unless you have a reason not to. Marking it Required (or Default On) is what makes setup one step for your developers: the skill is already loaded when they open Cursor, so they just ask for something OutSystems-related and the agent walks them through the tenant prompt and sign-in. Leaving it opt-in means each developer must find and enable the plugin first, and until they do the agent has no OutSystems skill at all.

**Individual User (after admin installs):** Open Cursor and ask anything OutSystems-related. The agent prompts for your tenant hostname, writes your personal `~/.cursor/mcp.json` (creating it if you don't have one — the plugin's own `cursor/mcp.json` is a read-only template and is never edited), and completes setup automatically.

No team admin, or on an individual plan? Use the **Cursor CLI** path above; it works on every plan.

**Update:** a team admin refreshes the `OutSystems/outsystems-mcp` import under **Plugins** > **Team Marketplaces** in the dashboard; developers then get the new plugin version. How Cursor resolves a new plugin version, and whether it pulls one without that refresh, is unverified. The `~/.cursor/mcp.json` entry needs no update.

See [cursor/README.md](cursor/README.md) for detailed setup instructions and version alignment requirements.

## Install - M365 Copilot (web browser)

Currently, this assistant does not support custom MCP servers.

**Skill, MCP server and Update:** not applicable. Without custom MCP server support there are no tools for the skill to drive, so neither artifact is installed here.

## Install - other AI assistants (best effort)

For other agentic harnesses (Codex CLI, Continue, Cline, Aider, etc.), this is a best-effort install path — the MCP server is a stock streamable-HTTP MCP endpoint with OAuth + Dynamic Client Registration, so most harnesses should be able to wire it up, but we don't validate the flow ourselves. If something breaks, file an issue with the symptoms.

**MCP server:** Step 2 of the prompt below registers it.

**Skill:** Step 3 of the prompt below injects it into the harness's instructions.

Paste into your harness:

```
Install the OutSystems MCP server.
Step 1: ask me for my OutSystems tenant hostname (something like `mycompany.outsystems.dev`).
Step 2: register `outsystems` as an MCP server in this harness's configuration, pointing at `https://<my-tenant>/mcp` over the streamable HTTP transport. Use whatever wiring the harness prefers — a CLI command, a settings UI, or hand-editing the harness's MCP config file. The server requires OAuth and supports Dynamic Client Registration, so no shared `client_id` setup is needed, and do not pin a fixed callback port: let the harness pick its own loopback port.
Step 3: fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/SKILL.md and inject its contents into this harness's instructions/rules/system-prompt mechanism (e.g. the system prompt rules file in Cline, a repo instruction file consumed by Aider, the system prompt config for Continue, etc.). The skill covers conventions (OML stays server-side, polling shape for long-running tools, error category enums, mentor session round-trip) that the tool descriptions alone don't fully convey.
Step 4: trigger authentication. If the harness synthesizes per-server `authenticate` / `complete_authentication` tools after registration (as Claude Code does — they're a client convenience, not server tools), call those (lazy on first tool call). Otherwise let the harness's built-in MCP auth UI handle the OAuth handshake.
Step 5: depending on the harness, the new MCP server may not be visible until you reload its MCP config or restart. If the harness has a CLI to list registered MCP servers (similar to `claude mcp list`), run it to check whether `outsystems` is visible — if not, tell me to restart the harness. Once the tools appear, ask me anything OutSystems-related to confirm the install is complete.
```

**Update:** [SKILL.md](SKILL.md) is a living document that changes with new releases, and the copy Step 3 injected stays as it was on the day you installed. Paste into your harness:

```
Update the OutSystems skill in this harness.
Find the copy an earlier install injected into this harness's instructions/rules/system-prompt mechanism: the block that begins with the heading `# OutSystems - Remote MCP` and ends where the text of its last section, `## Feedback`, ends. Fetch https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/SKILL.md and replace that whole block with the fetched contents, leaving everything else in place. If you can't find the block, or can't tell where it ends, write nothing and tell me what you found.
```

## Beta skills

The following skills are Beta Features. OutSystems provides Beta Features to collect customer feedback on non-final capabilities. A Beta Feature can change significantly, including through breaking changes, or OutSystems can discontinue it. For the terms that apply, refer to <https://www.outsystems.com/legal/beta-features-agreement>.

- **outsystems-app-architecture**: produces an interactive HTML graph of one app: screens, actions with their signatures, entities with attributes and relationships, roles, dependencies, and where the app is deployed. It ships in the Claude Code, Claude Desktop, Kiro, and Cursor App plugins, next to the main OutSystems skill. The Copilot, Cursor CLI, and other-assistant install paths do not include it.
- **outsystems-dependency-impact**: produces an HTML explorer of who depends on a library, agent, or connection, from the platform's deletion-impact analysis (read-only: nothing is deleted). It ships in the Claude Code, Claude Desktop, Kiro, and Cursor App plugins, next to the main OutSystems skill. The Copilot, Cursor CLI, and other-assistant install paths do not include it.
- **outsystems-design-to-app**: builds a draft OutSystems app through Mentor from a design source: a Figma URL, a screenshot, an HTML mockup, or front-end code. It ships in the Claude Code, Claude Desktop, Kiro, and Cursor App plugins, next to the main OutSystems skill. The Copilot, Cursor CLI, and other-assistant install paths do not include it.
- **outsystems-spec-driven-build**: builds a draft OutSystems app through Mentor from a text-only spec: your own markdown spec, a short interview, or the bundled example. It checks the spec first (a defined role for every screen and the entities, with warnings when relationships or integrations are missing), then has Mentor build the whole app in one turn, with sample data loaded by a timer when the app is published. It ships in the Claude Code, Claude Desktop, Kiro, and Cursor App plugins, next to the main OutSystems skill, but runs a Python script, so Claude Desktop's Chat tab, which has no shell, can't run it. The Copilot, Cursor CLI, and other-assistant install paths do not include it.
- **outsystems-tenant-architecture**: produces an interactive HTML graph of every asset in your tenant, where each one is deployed, a 7-day Production traffic and error overlay, and an AI governance view (model providers, Trial vs Customer entitlement). It ships in the Claude Code, Claude Desktop, Kiro, and Cursor App plugins, next to the main OutSystems skill. The Copilot, Cursor CLI, and other-assistant install paths do not include it.

The three architecture skills (`outsystems-tenant-architecture`, `outsystems-app-architecture`, and `outsystems-dependency-impact`) load in Claude Code when a request matches them. Cursor and Kiro receive the same folders, but running them there has not been validated yet. Unlike the main skill, each one runs a Python script that turns the tool results into an HTML page, so the agent needs:

- a shell it can run commands in, with Python 3.8 or later (standard library only); Claude Desktop's Chat tab has no shell, so it cannot run them;
- the OutSystems MCP server connected and signed in. The scripts never call the server themselves: the agent fetches the data with its own MCP connection and the scripts only read the saved results.

They are validated on Claude Code, which also keeps the largest tool results out of the conversation by saving them to disk. A harness without that passes every result through the conversation, so the same run costs more tokens. The pages are written to your working folder; they embed your tenant data and, when opened, load fonts from Google Fonts and, for the two graph pages, a graph library from unpkg or jsDelivr. They keep a cache in `~/.cache/outsystems-skills`, a hidden `.cache` folder in your home folder on every operating system (macOS and Windows included), and reuse it for up to an hour (a day for dependency-impact analyses); delete that folder to clear it.

`outsystems-design-to-app` is validated on Claude Code; Cursor and Kiro receive the same folder, but running it there has not been validated yet. It runs no script: the agent sends the design, the spec it writes and the sample data to your tenant's Mentor, reads Figma frames through your own Figma MCP server when the source is a Figma URL, and keeps its build files in a `design-to-app` folder in your workspace. It asks before it creates an app and before every publish, and after publishing it opens the app in a local browser to compare it with the design, asking you to sign in when the screen needs it.

`outsystems-spec-driven-build` is validated on Claude Code; Cursor and Kiro receive the same folder, but running it there has not been validated yet. It needs a shell with Python 3.8 or later (standard library only; on Windows the interpreter may be `python` or `py -3`) to run its script, which checks the spec and writes the Mentor prompt and a build report; the script never calls the server. The agent sends the spec text to your tenant's Mentor and keeps the spec, the saved Mentor results and the report in a `spec-driven-build` folder in your workspace. It asks before it creates an app and before it publishes.

## Troubleshooting

| Symptom | Cause and fix |
| :-- | :-- |
| Tool calls fail with `403` and `tenant_not_allowed` | Your tenant is not yet enabled for the MCP server. This is a server-side allowlist and no amount of reinstalling changes it. Ask your OutSystems contact to have the tenant enabled, or open an issue here with the tenant hostname. |
| The `authenticate` tool isn't loaded (Claude Code) | The MCP server isn't loaded, or the session started before it was. Run `claude mcp list`. Expect `plugin:outsystems:outsystems` (or a user-scope `outsystems` from an earlier install) with your tenant URL; if it's there, restart Claude Code. If the plugin is installed (`claude plugin list` shows `outsystems@outsystems`) but the list prints `No MCP servers configured` (ignore its `claude mcp add` hint) or has no `outsystems` line, the `tenant_hostname` option is unset: see the next row. If the plugin isn't installed, re-run the Claude Code recipe from Step 2. |
| The plugin's server is missing from `claude mcp list`, `claude --debug` prints `Plugin option "tenant_hostname" isn't set`, or the server URL reads `https://https://...` (Claude Code) | The plugin builds its server URL from your tenant hostname and nothing validates the value you give it. Set or fix it with `claude plugin install outsystems@outsystems --config tenant_hostname=<my-tenant>` (a bare hostname, no scheme prefix, no path; on an installed plugin the command only updates the option) or with `/plugin configure outsystems@outsystems` inside Claude Code, then restart Claude Code. Claude Desktop and the VS Code extension may not prompt for the option when installing the plugin ([anthropics/claude-code#89749](https://github.com/anthropics/claude-code/issues/89749)); use the terminal command above. |
| The `status-watcher` agent stops at once, reporting that a status tool is missing (Claude Code) | The session reaches OutSystems through a server named neither by the plugin nor `outsystems` (for example one added as `outsystems-dev`), so the agent's tools, which are named `mcp__plugin_outsystems_outsystems__<tool>` and `mcp__outsystems__<tool>`, don't exist in the session. Nothing breaks: the assistant polls in the main conversation as before, without the saving. Use the plugin's server, as the Claude Code install describes, or register the server as `outsystems`. |
| Auth fails with `OAuth callback port <port> is already in use ...` (Claude Code) | An earlier setup step pinned a fixed callback port, and the pin sits in your own config, so updating the plugin does not clear it. The plugin's own server never pins a port, so if the pin is in your MCP config at all it is in a user-scope `outsystems` entry from an earlier install. Run `claude mcp get outsystems`; if it reports no server named `outsystems`, skip to the environment and port checks at the end of this row. Otherwise note the reported URL, which you need to re-add. If it reports a `callback_port`, unpin it in the reset below. If it does not, the pin is not in your MCP config: check for a callback-port override in your environment, then for another process holding the port with `lsof -nP -iTCP:<port> -sTCP:LISTEN`, or `netstat -ano \| findstr :<port>` on Windows. |
| Auth never triggers in a non-interactive session | The OAuth flow needs a browser and a loopback callback, so it cannot complete in a headless or piped session. Authenticate once in an interactive session first; that sign-in is reused afterwards. |
| No browser window opens (Claude Desktop), or you can't tell if one did | The `mcp-remote` local proxy may need a moment before it opens the sign-in window on the first tool call, or after a sign-in expires. Retry the request once. If a window still never appears, check the `npx` PATH row below first — a proxy that can't resolve `npx` never opens a window at all. If that isn't it, remove and re-add the `outsystems` entry in your MCP config, restart Claude Desktop, and try again; if it persists, open an issue here. |
| "Server Disconnected" or "failed authorization" | Usually a stale or partial OAuth grant. Run the reset below. If it persists, the tenant hostname is likely wrong: confirm it resolves and that `https://<my-tenant>/mcp` returns `401` rather than `404`. |
| Nothing connects on Windows, or `npx` is "not found" | Applies to the Claude Desktop local-proxy install only. Claude Desktop launches processes with a minimal PATH, and a broken, stale, or mistyped `"command"` value looks identical to Desktop. macOS/Linux: replace whatever the `"command"` value currently is with the full path from `which npx`. Windows: if the entry is `cmd`-shaped (its `args` begin with `/c`), ensure `"command"` is `"cmd"` — restore it if it is anything else — then replace whatever text stands in for `npx` inside the `/c` argument string with the `.cmd` path from `where npx` (the line ending in `.cmd`), quoting it if it contains a space (e.g. `"C:\Program Files\nodejs\npx.cmd"`); if instead the entry invokes `npx` directly (its `args` begin with `mcp-remote`), apply the macOS/Linux remedy above using the `.cmd` path from `where npx` as the `"command"` value, without converting it to the `cmd`-shaped form. Restart Claude Desktop again after any change and retry. |
| Browser windows keep reopening, and the proxy log shows `EADDRINUSE` | Applies whenever you reach the server through the `mcp-remote` proxy, which is the Claude Desktop install above and any harness you wired up that way. On `mcp-remote` versions before 0.13.5, the proxy reused the callback port saved in its own client registration and exited before sign-in completed, so the host restarted it and no sign-in was ever stored; upgrading to 0.14.0 or later (`npm install -g mcp-remote@latest`, the minimum the `IssuerMismatchError` row below requires) resolves this unless you pinned a specific port yourself, in which case a conflict on that exact port still fails. Clear the saved registration, in the reset below. |
| Sign-in fails and the proxy log shows `IssuerMismatchError: Issuer mismatch in authorization response (RFC 9207)` ending in `received undefined` | Applies whenever you reach the server through the `mcp-remote` proxy. Releases 0.9.0 through 0.13.5 check the `iss` parameter of the sign-in callback but drop it before the check, so every sign-in fails on any tenant; 0.14.0 fixed it. `npx mcp-remote` runs your global install when there is one, so an old global copy keeps failing until you upgrade it. Run `npm install -g mcp-remote@latest`, confirm `npm ls -g mcp-remote` reports 0.14.0 or later, then restart the host (Claude Desktop, or whichever harness launches the proxy) and sign in again. Do not pin an older release such as 0.8.7 instead: it predates the check, so it signs in only by dropping the protection the check provides. |
| The Cursor agent ignores the OutSystems skill | An earlier version of the Cursor CLI recipe saved the skill to `.cursor/rules/outsystems.md`. Cursor's rules loader only enumerates `.mdc` files carrying rule frontmatter, so a plain `.md` there never loaded. Move it to `AGENTS.md` in your workspace root, which Cursor loads verbatim, and delete the old copy. |
| Tools are listed but greyed out (Visual Studio) | MCP tools are disabled by default. Enable them in the Tools picker. |
| Nothing appears at all on a Copilot Business or Enterprise plan | An admin must enable the "MCP servers in Copilot" policy. |
| No "Add custom connector" button in Claude Desktop | The native connector flow is not a working install path today regardless of button visibility; use the local-proxy steps in the Claude Desktop section. |
| Can't find a plugin-install option in Claude Desktop | Plugins require a paid plan (Pro, Max, Team, Enterprise); on Free there is no plugin install surface. On a paid plan, an Enterprise admin may also restrict which plugins install. |
| The agent isn't asking for confirmation before a destructive tenant operation on Claude Desktop | Usually the plugin isn't installed, or you're on the Free plan where plugins aren't available: install the plugin above, or read [SKILL.md](SKILL.md) manually and apply its rules yourself. If the plugin is installed and this still happens, Desktop's Chat tab may not be applying the skill's rules; open an issue here with what you observed. |

### Reset

For a routine skill update, use the **Update** step in your harness's section. When an install is wedged and updates don't stick, do a clean cycle rather than reinstalling on top:

1. Write down the whole `outsystems` entry first, on any harness, because removing it destroys the only record of your tenant URL and of any extra proxy arguments, and later steps need both. On Claude Code, `claude mcp get outsystems` prints the URL and the scope. Then remove the server: `claude mcp remove outsystems`, or delete the `outsystems` entry from the relevant config file on other harnesses. Removing it is also what drops a callback port pinned by an earlier setup step. Omitting `-s` clears whichever scope holds the entry; if the name exists in more than one the command removes nothing and lists them, so repeat it per scope with `-s <scope>`, and leave a `project` scope alone if the config is shared with other people. If the server comes from the plugin instead (`plugin:outsystems:outsystems` in `claude mcp list`), there is no entry to remove, but write down the hostname that line shows before step 2: uninstalling the plugin also deletes the option, and the reinstall in step 6 needs the value again. To change the tenant without a reset, run `claude plugin install outsystems@outsystems --config tenant_hostname=<new-tenant>` (bare hostname, no scheme prefix, no path) or `/plugin configure outsystems@outsystems`.
2. Uninstall the plugin or Power, if you installed one.
3. Clear the host's cache (in Claude Desktop: **Help > Troubleshooting > Clear cache**). If you reach the server through the `mcp-remote` proxy, also do the following before restarting.

   <details>
   <summary>Clear the saved proxy registration, only if you reach the server through the mcp-remote proxy</summary>

   The proxy saves its own OAuth client registration under `~/.mcp-auth`, and that record pins the callback port it reuses on every later launch. You do not need to touch that folder to clear it: give the proxy a different port on the command line and it discards the stale registration itself.

   1. Quit the host, so it stops relaunching the proxy while you work.
   2. Pick a port nothing is using. `lsof -nP -iTCP:<port> -sTCP:LISTEN` on macOS or Linux, `netstat -ano | findstr :<port>` on Windows, should print nothing for it.
   3. Add that port as the last argument of the `outsystems` entry in the host's config, after the URL, for example `{"command": "npx", "args": ["mcp-remote", "https://<my-tenant>/mcp", "<free port>"]}`.
   4. Continue with step 4 of the reset. On the next launch the proxy sees a port that disagrees with its saved registration, deletes that registration, and registers again on the port you gave it.

   The proxy always records some port, so this replaces a stuck one rather than switching pinning off; that is an upstream limitation rather than a setting. Removing the argument again later just makes the proxy reuse the port it last recorded. Expect one extra sign-in, because the saved sign-in belonged to the registration that was replaced.

   If a different port does not help, the folder itself can be removed: it is `~/.mcp-auth` (or the folder the proxy is configured to use). Removing it makes every server you reach through this proxy sign in again, so prefer the port change above, and never delete it to work around a port conflict you have not confirmed.

   None of this is a permanent fix for a pinned port: it stays mandatory once you've added it as an argument, so a genuine conflict on that exact port still fails outright. The underlying orphaned-proxy failure returns if the host exits without shutting the proxy down, leaving an orphaned proxy still running and holding the port. When that happens you do not need this block at all: find the orphan with `lsof -nP -iTCP:<port> -sTCP:LISTEN`, or `netstat -ano | findstr :<port>` on Windows, and stop it. A second proxy started while the first is still running normally waits for it, but only while the first one's lock is under 30 minutes old; past that the wait is skipped and a fresh proxy tries to bind the held port. On Windows the proxy never waits at all. mcp-remote 0.13.5 fixed that bind to fall back to a random port instead of crashing, per [mcp-remote PR #262](https://github.com/punkpeye/mcp-remote/pull/262); an older, cached `mcp-remote` still crashes there, so upgrade it to 0.14.0 or later (`npm install -g mcp-remote@latest`) before working through this block.

   </details>

4. Restart the host.
5. Refresh the plugin or Power source so you get the current recipe, if you installed from one: `claude plugin marketplace update outsystems` (Claude Code), refresh the marketplace source from Claude Desktop's plugin management UI if it exposes one, or otherwise uninstall the plugin, remove and re-add the marketplace, and reinstall (Claude Desktop), or update the Power from Kiro's Powers panel (`git pull` in your clone if you installed from a local registry file). Reinstalling from a stale source re-applies the old setup command.
6. Reinstall from the recipe above.

### Getting logs

Attach these when opening an issue; they are what makes a report actionable.

- **Claude Code**: `claude mcp list` output, plus `claude --debug` for a failing session.
- **Claude Desktop**: `~/Library/Application Support/Claude/logs/` on macOS, `%APPDATA%\Claude\logs\` on Windows, `~/.config/Claude/logs/` on Linux. There is a per-server log file alongside the main one.
- **VS Code**: the MCP server output channel, via `MCP: List Servers` then **Show Output**.
- **Kiro**: the Powers and MCP output channels.

Remove your tenant hostname and any sign-in data from the logs before posting.

## Support and privacy

### Support

Customers with an active OutSystems subscription can report issues with the MCP Server through the [OutSystems Support Portal](https://success.outsystems.com/support/home/), handled under the support terms and SLAs of their subscription. GitHub Issues in this repository are intended for community discussion, bug reports, and feature requests, and are addressed on a best-effort basis.

When you open an issue in the [outsystems-mcp issue tracker](https://github.com/OutSystems/outsystems-mcp/issues), attach the logs listed under [Getting logs](#getting-logs). For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

### Privacy policy

The OutSystems privacy policy is the [OutSystems Privacy Statement](https://www.outsystems.com/legal/terms-of-use/privacy-statement). It describes how OutSystems processes personal data.

OutSystems hosts the MCP server. It signs you in through your own OutSystems tenant, takes your user and tenant identity from that sign-in, and acts on that tenant's apps and environments on your behalf. How OutSystems processes the data in your tenant is governed by your organization's agreement with OutSystems. For customers on the OutSystems Master Subscription Agreement, that includes the [Data Processing Agreement](https://www.outsystems.com/legal/outsystems-msa/data-processing-agreement/). Feedback that you send through the feedback tool goes to OutSystems so that the maintainers can act on it.
