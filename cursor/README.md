# Cursor - OutSystems MCP Plugin

This directory ships the OutSystems MCP plugin for Cursor, available for both Cursor app and Cursor CLI.

## Install - Cursor App (Plugin)

### Team / Enterprise Plans (Admin Required)

If your organization uses a Cursor Team or Enterprise plan, a **team admin** must install the plugin to your team's Marketplace first.

**Team Admin Installation:**
1. Open Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → **Import from Repo**
2. Enter: `https://github.com/OutSystems/outsystems-mcp`
3. Review the `outsystems` plugin and save (Default On / Required as needed)

**Individual User Setup (after admin installs plugin):**
1. Open Cursor
2. In the chat, ask anything OutSystems-related (e.g., "list my apps")
3. The agent will ask for your **OutSystems tenant hostname** (e.g., `mycompany.outsystems.dev`)
4. The agent configures `~/.cursor/mcp.json` with the tenant URL
5. Complete OAuth sign-in when prompted
6. You're ready to use OutSystems tools

### Free Plans

Free Cursor plans do not support custom Marketplace plugins. Use **Cursor CLI** instead (see below).

## Install - Cursor CLI

Cursor CLI works on all plans and provides MCP management via terminal commands.

**Setup Steps:**

1. **Create MCP config** at `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):
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

2. **Install conventions file** (optional but recommended):
   - Fetch: https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/cursor/skills/outsystems/SKILL.md
   - Save to `.cursorrules` in your workspace root
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

Update all three together in the same commit when bumping the version.

## Skill Docs Lockstep

The Cursor skill doc is included in the plugin and deployed via `cursor/.cursor-plugin/plugin.json`. It must stay synchronized with the other harness skill docs:
- `skills/outsystems/SKILL.md` (Claude Code)
- `kiro/outsystems/steering/skill.md` (Kiro)
- `copilot/skill.md` (GitHub Copilot)
- `SKILL.md` (root, generic)

All five files carry identical `## Rules`, `## Workflows`, and `## Feedback` sections. Any behavioral change to one must be applied to all five.

Use the lockstep grep check before opening a PR:
```bash
PHRASE="<distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All counts must be equal.
