# CLAUDE.md

Guidance for Claude Code (and other coding agents) when working in this repository.

## Supported harnesses

`README.md` ships an install path per harness. This table is the canonical list of what "all supported harnesses" means. Update it in the same PR that adds or drops a path.

| Harness | Skill doc | How the skill doc arrives | MCP config target | Server key |
| :-- | :-- | :-- | :-- | :-- |
| Claude Code | `skills/outsystems/SKILL.md` | automatic, via `plugin.json`'s `skills` key | user scope, written by `claude mcp add` | n/a |
| Claude Desktop | none | **not delivered** | `claude_desktop_config.json` | `mcpServers` |
| Kiro Chat | `kiro/outsystems/steering/skill.md` | automatic, via the Power's `steering/` directory | `~/.kiro/settings/mcp.json` | `mcpServers` |
| Copilot in VS Code | `copilot/skill.md` | manual copy to `.github/copilot-instructions.md` | `.vscode/mcp.json`, or the user config | `servers` |
| Copilot in CLI | `copilot/skill.md` | manual copy to `.github/copilot-instructions.md` | `~/.copilot/mcp-config.json` | `mcpServers` |
| Copilot in Visual Studio | `copilot/skill.md` | manual download to `.github/copilot-instructions.md` | `<SolutionDir>\.mcp.json`, or `%USERPROFILE%\.mcp.json` | `servers` |
| Cursor App | `cursor/skills/outsystems/SKILL.md` | automatic, via `.cursor-plugin/plugin.json` | Team Marketplace install (Team/Enterprise plan required) | `mcpServers` |
| Cursor CLI | `cursor/skills/outsystems/SKILL.md` | manual copy to `.cursorrules` | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project) | `mcpServers` |
| M365 Copilot | n/a | n/a | unsupported: no custom MCP servers | n/a |
| Other assistants | `SKILL.md` (root) | manual fetch, best effort | harness-specific | harness-specific |

Two traps the table encodes:

- **`servers` vs `mcpServers`.** VS Code and Visual Studio read `servers`; Copilot CLI, Kiro, Claude Desktop, and Cursor CLI read `mcpServers`. `copilot/mcp.json` carries both keys so each surface copies the one it needs. Writing the wrong key fails silently: the file still parses and no server appears. (Cursor also has a `.vscode/mcp.json` (IDE-only) that uses `servers`, but the CLI ignores it.)
- **Claude Desktop receives no skill doc.** Its install path wires up the MCP server and nothing else, so Desktop users get the tools without the conventions, the confirm-before-destructive rule included. Every behavioral rule below reaches every harness except that one.
- **Cursor has dual paths: plugin-based (app) and file-based (CLI).** Cursor App users get the plugin from their Team Marketplace (requires Team/Enterprise plan + team admin approval). Each user then configures via agent setup, which writes `~/.cursor/mcp.json`. Cursor CLI users manually create `~/.cursor/mcp.json` or `.cursor/mcp.json` and use `agent mcp` commands. Both paths use `mcpServers` key; both skill docs are identical and ship via the plugin manifest.

### Validate every change against every supported harness

A change is not done because it works in the harness you happened to test. Before opening a PR, walk the table and account for every row. Exactly three outcomes are acceptable per harness: verified, not applicable with the reason, or a recorded gap with a follow-up. Silence on a row is none of the three.

What "verified" requires depends on what the change touches:

- **Skill-doc wording** -> the lockstep grep below, plus a read of the affected section in each doc that carries it.
- **MCP server config** -> resolve the config on that harness and confirm the server appears with the URL you expect, using whatever the harness offers (`claude mcp list`, Kiro's MCP panel, `/mcp show outsystems` in Copilot CLI, the VS Code MCP view). A config that parses is not a config that loaded.
- **Install recipe** -> run the pasted prompt end to end on that harness, from no configuration to a successful tool call.

Harnesses differ in ways that break otherwise-correct changes: the config key (`servers` vs `mcpServers`), the file location, whether tools are enabled by default (Visual Studio disables them), whether an admin policy gates MCP at all (Copilot Business/Enterprise), and whether the harness synthesizes its own `authenticate` tool or drives OAuth itself. Assume none of these transfer between harnesses without checking.

## Skill docs must stay in lockstep across hosts

This repo ships **five parallel skill documents**:

- `skills/outsystems/SKILL.md` is the Claude Code marketplace skill, consumed when a user runs `claude plugin install outsystems@outsystems`.
- `kiro/outsystems/steering/skill.md` is the Kiro Power steering doc, consumed by Kiro.
- `copilot/skill.md` is the GitHub Copilot skill doc, consumed by GitHub Copilot (VS Code, CLI, or Visual Studio).
- `cursor/skills/outsystems/SKILL.md` is the Cursor skill doc, consumed by Cursor CLI.
- `SKILL.md` at the repo root is the top-level fallback skill doc, consumed by hosts that look at the repo root or by anyone reading the repo on GitHub.

All five carry an identical `## Rules` section, and broadly the same `## Tools at a glance`, `## Caveats`, and `## Workflows` sections. **Any behavioral change to one MUST be applied to all five.** Updating only one creates a host-specific protection gap. For example, a confirm-before-destructive rule added to `skills/outsystems/SKILL.md` alone protects Claude Code users but leaves Kiro Power, Copilot, and Cursor users with no protection.

The common failure mode is to edit only `skills/outsystems/SKILL.md` because the marketplace install path points there. Don't.

### Check before opening a PR

After any skill-doc change, grep for a distinctive phrase from the change across all five files and confirm the count matches:

```bash
PHRASE="<a distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All five counts must be equal. If they aren't, the change is incomplete and the PR will create a host-specific drift.

### Exception: setup / installation flows

Setup steps legitimately diverge between the harnesses (Claude Code uses `claude mcp add`, Kiro Power patches `~/.kiro/settings/mcp.json`, GitHub Copilot uses VS Code/Visual Studio settings or Copilot CLI config, the root SKILL.md describes the wire-level tool names without prescribing a host). The lockstep rule applies to `## Rules` and to behavioral guidance, not to host-specific install recipes.

### Exception: host-specific affordances

Host-specific UI surfaces (typed shortcuts, hotkeys) live only in the doc for the host that has them. The Claude Code marketplace plugin ships slash commands under `commands/` (declared in `.claude-plugin/plugin.json`'s `commands` key); Kiro Powers do not have an equivalent. So mentions of `/outsystems-feedback` and similar slash-command trigger phrases belong only in `skills/outsystems/SKILL.md`, not in `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, `cursor/skills/outsystems/SKILL.md`, or root `SKILL.md`. The underlying *behavior* (what the agent does on the trigger) still has to lockstep across all five docs.

Naming note: slash-command filenames become the command name a user types. Claude Code ships a built-in `/feedback` that routes to Anthropic's issue tracker, so a plugin file named `commands/feedback.md` is shadowed by the host and never fires. Every plugin slash MUST be prefixed with `outsystems-` (`commands/outsystems-feedback.md` → `/outsystems-feedback`) so the host-vs-plugin collision surface is closed by the file name alone.

`commands/` is a Claude-Code-plugin-only directory. There is no Kiro analog, no Copilot analog, no Cursor analog, and no root analog; do not create one. Behavioral guidance about a command's effect still lands in all five skill docs per the main lockstep rule.

### Manifest version lockstep

Three sets of files declare plugin versions and they must stay in sync on every bump:

**Claude:**
- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`

**Cursor:**
- `cursor/.cursor-plugin/plugin.json` -> `version`
- `.cursor-plugin/marketplace.json` -> `plugins[0].version`

`claude plugin update outsystems@outsystems` keys off `.claude-plugin/marketplace.json`'s version. Cursor plugin updates via Team Marketplace also key off `.cursor-plugin/marketplace.json`. Forgetting to bump these means users already on the prior version see "already at the latest" and never pull the new content. Always bump all four files (Claude + Cursor pairs) in the same commit, keeping both Claude and Cursor versions aligned.
