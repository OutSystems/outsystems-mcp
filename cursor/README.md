# Cursor - OutSystems MCP Plugin

This directory ships the OutSystems MCP plugin for Cursor, available for both Cursor app and Cursor CLI.

## Install - Cursor App (Plugin)

### Team / Enterprise Plans (Admin Required)

If your organization uses a Cursor Team or Enterprise plan, a **team admin** must install the plugin to your team's Marketplace first.

**Team Admin Installation:**
1. Open Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → **Import from Repo**
2. Enter: `https://github.com/OutSystems/outsystems-mcp`
3. Review the `outsystems` plugin and save it as **Required** — or at minimum **Default On**

> **Mark it Required.** This is the single biggest thing you can do to make setup painless for your developers: the skill is loaded the moment they open Cursor, so setup collapses to "ask for something OutSystems-related and answer the tenant prompt". Left opt-in, every developer has to discover and enable the plugin first, and until they do the agent has none of the OutSystems conventions — it will guess at config locations and formats.

**Individual User Setup (after admin installs plugin):**
1. Open Cursor
2. In the chat, ask anything OutSystems-related (e.g., "list my apps")
3. The agent will ask for your **OutSystems tenant hostname** (e.g., `mycompany.outsystems.dev`)
4. The agent writes your personal `~/.cursor/mcp.json` with the tenant URL, creating that file if you don't have one yet
5. Complete OAuth sign-in when prompted
6. You're ready to use OutSystems tools

> The `cursor/mcp.json` shipped in this plugin is a **reference template, not your config**. It lives inside the read-only installed plugin directory, so the agent copies its shape into `~/.cursor/mcp.json` instead of editing it in place. A refusal to write inside the plugin directory is correct behavior, not a broken install.

### Free / Individual Plans

Free and individual Cursor plans do not support custom Marketplace plugins. Use **Cursor CLI** instead (see below).

## Install - Cursor CLI (all plans, individual accounts included)

Cursor CLI works on every plan — individual accounts included, no team admin or Marketplace plugin required — and provides MCP management via terminal commands.

**Setup Steps:**

1. **Create or edit the MCP config** at `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project). Both files are merged; if the same server name appears in both, the project-level entry takes priority. Read it first if it exists and preserve your other entries:
   ```json
   {
     "mcpServers": {
       "outsystems": {
         "url": "https://<my-tenant>/mcp"
       }
     }
   }
   ```
   Replace `<my-tenant>` with your OutSystems tenant hostname (e.g., `mycompany.outsystems.dev`).

   Only these two files matter. Don't copy an entry over from another assistant's MCP config (`.vscode/mcp.json`, `.mcp.json`, `~/.copilot/mcp-config.json`, `~/.claude.json`, `claude_desktop_config.json`, `~/.kiro/settings/mcp.json`, or any other assistant's file) — they use different keys (`servers` vs `mcpServers`) and schemas, and a block moved across silently fails to load.

2. **Install conventions file** (optional but recommended):
   - Fetch: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/skills/outsystems/SKILL.md
   - Save to `AGENTS.md` in your workspace root — Cursor loads it verbatim, with no frontmatter requirement
   - Don't save it under `.cursor/rules/`: that loader only picks up `.mdc` files carrying rule frontmatter (`description`, `globs`, `alwaysApply`), so a plain `.md` copy there is never loaded
   - If `AGENTS.md` already holds an OutSystems conventions doc that another assistant's setup installed, keep it rather than adding a second copy beside it — and note that a later Copilot setup in the same workspace should then be pointed at `.github/copilot-instructions.md`, the path Copilot actually reads
   - This provides behavioral guidelines for the agent

3. **Verify and authenticate**:
   ```bash
   agent mcp list                  # See registered servers
   agent mcp enable outsystems     # Approve if it shows "needs approval"
   agent mcp login outsystems      # OAuth sign-in (opens browser)
   ```

4. **Test in agent**:
   ```bash
   agent "list 10 of my outsystems apps"
   ```

## Version Alignment

Cursor and Claude plugin versions must stay in sync:
- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`
- `cursor/.cursor-plugin/plugin.json` → `version`
- `.cursor-plugin/marketplace.json` → `plugins[0].version`

Update all four together in the same commit when bumping the version.

## Skill Docs Lockstep

The Cursor skill doc is included in the plugin and deployed via `cursor/.cursor-plugin/plugin.json`. It must stay synchronized with the other harness skill docs:
- `skills/outsystems/SKILL.md` (Claude Code)
- `kiro/outsystems/steering/skill.md` (Kiro)
- `copilot/skill.md` (GitHub Copilot)
- `SKILL.md` (root, generic)

All five files carry a `## Rules` section that is identical but for one wording drift in the "Go straight to the task" bullet, and broadly the same `## Tools at a glance`, `### Caveats`, `## Workflows`, and `## Feedback` sections. Any behavioral change to one must be applied to all five, and to `kiro/outsystems/POWER.md`, whose `## Conventions` section carries the same rules for Kiro operators while sitting outside the grep below.

Use the lockstep grep check before opening a PR:
```bash
PHRASE="<distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All counts must be equal for a phrase in a lockstepped section. A phrase that also appears in a host-specific setup section legitimately differs; see CLAUDE.md for how to count those.
