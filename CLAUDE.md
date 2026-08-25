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
| Cursor App | `cursor/skills/outsystems/SKILL.md` | automatic, via `cursor/.cursor-plugin/plugin.json` | Team Marketplace install (Team/Enterprise plan required) | `mcpServers` |
| Cursor CLI | `cursor/skills/outsystems/SKILL.md` | manual copy to `.cursor/rules/outsystems.md` | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project) | `mcpServers` |
| Codex CLI | `codex/skills/outsystems/SKILL.md` | automatic, via `codex/.codex-plugin/plugin.json`'s `skills` key | `~/.codex/config.toml`, written by `codex mcp add` | `mcp_servers` |
| Codex in the ChatGPT desktop app (macOS) | `codex/skills/outsystems/SKILL.md` | automatic, same plugin — installed from either surface | `~/.codex/config.toml`, shared with the CLI | `mcp_servers` |
| Codex IDE extension | `codex/skills/outsystems/SKILL.md` | manual copy to `~/.agents/skills/outsystems/SKILL.md` or `$REPO_ROOT/.agents/skills/outsystems/SKILL.md`; **plugins do not work here** | `~/.codex/config.toml`, shared with the CLI | `mcp_servers` |
| M365 Copilot | n/a | n/a | unsupported: no custom MCP servers | n/a |
| Other assistants | `SKILL.md` (root) | manual fetch, best effort | harness-specific | harness-specific |

Five traps the table encodes:

- **`servers` vs `mcpServers` vs `mcp_servers`.** VS Code and Visual Studio read `servers`; Copilot CLI, Kiro, Claude Desktop, and Cursor CLI read `mcpServers`; Codex reads an `[mcp_servers.<name>]` table in **TOML**, not JSON. `copilot/mcp.json` carries both JSON keys so each surface copies the one it needs. Writing the wrong key fails silently: the file still parses and no server appears. (Cursor also has a `.vscode/mcp.json` (IDE-only) that uses `servers`, but the CLI ignores it.)
- **Claude Desktop receives no skill doc.** Its install path wires up the MCP server and nothing else, so Desktop users get the tools without the conventions, the confirm-before-destructive rule included. Every behavioral rule below reaches every harness except that one.
- **Cursor has dual paths: plugin-based (app) and file-based (CLI).** Cursor App users get the plugin from their Team Marketplace (requires Team/Enterprise plan + team admin approval). Each user then configures via agent setup, which writes `~/.cursor/mcp.json`. Cursor CLI users manually create `~/.cursor/mcp.json` or `.cursor/mcp.json` and use `agent mcp` commands. Both paths use `mcpServers` key; both skill docs are identical and ship via the plugin manifest.
- **Codex is three surfaces over one config, and only two of them take plugins.** Codex CLI, the ChatGPT desktop app, and the IDE extension all read `~/.codex/config.toml` — MCP servers, marketplace registrations, and per-plugin enable state included — so an install done in the CLI is an install done everywhere. But the **IDE extension has no plugin support**, so its users need the skill as a file. Codex discovers skills at `<dir>/.agents/skills/<name>/SKILL.md` in repo scope (`$REPO_ROOT` and every directory from the CWD up), user scope (`~/.agents/skills`), and admin scope (`/etc/codex/skills`) — all three verified on Codex CLI 0.148.0, along with the older `~/.codex/skills/<name>/SKILL.md`. A repo-scoped skill directory does exist, so don't send repo-scoped users to `AGENTS.md`, which is always-on context rather than an on-demand skill.
- **Codex's marketplace index lives outside the plugin directory.** Claude reads `.claude-plugin/marketplace.json` and Cursor reads `.cursor-plugin/marketplace.json`, both at the repo root; Codex reads `.agents/plugins/marketplace.json`, also at the repo root, and resolves each entry's `source.path` **relative to the marketplace root, which is the repo root** rather than the marketplace file's directory. That is why the entry is `./codex` and not `./plugins/outsystems` (what Codex's own `plugin-creator` scaffold writes for personal plugins). Verify a change to either file by resolving it, not by reading it: `codex plugin marketplace add .` then `codex plugin list` prints the path it actually resolved. Codex would also accept `.claude-plugin/marketplace.json` as a legacy-compatible index, but it takes the `.agents` one here — confirmed by `codex plugin list` naming that file.

**Codex 0.147.0 is the floor.** `codex plugin` and skill frontmatter landed there, so neither install path exists on anything older; say so in every Codex-facing doc that describes an install. Verified against 0.148.0.

**Plan gating differs per harness, and Codex is the permissive one.** Codex needs no paid plan: the CLI plugin browser, `codex plugin`, and `codex mcp` all work on Free, Go, Plus, Pro, and API-key sign-in. Cursor App is the opposite (Team/Enterprise plan plus a team admin), and Copilot Business/Enterprise needs an admin policy. What Codex *does* have is managed-workspace policy: on ChatGPT Business, Enterprise, and Edu an admin `requirements.toml` can set `marketplaces.restrict_to_allowed_sources` (blocking `codex plugin marketplace add` for this repo), pin `features.plugins` off, or ship an `mcp_servers` allowlist that must match both the server name **and** its identity (here, the URL). All of these fail quietly: the command reports success, Codex falls back to a compatible value, and nothing appears. When testing on a managed machine, treat a silent no-op as policy before treating it as a bug in this repo.

### Validate every change against every supported harness

A change is not done because it works in the harness you happened to test. Before opening a PR, walk the table and account for every row. Exactly three outcomes are acceptable per harness: verified, not applicable with the reason, or a recorded gap with a follow-up. Silence on a row is none of the three.

What "verified" requires depends on what the change touches:

- **Skill-doc wording** -> the lockstep grep below, plus a read of the affected section in each doc that carries it.
- **MCP server config** -> resolve the config on that harness and confirm the server appears with the URL you expect, using whatever the harness offers (`claude mcp list`, `codex mcp list` plus `codex plugin list`, Kiro's MCP panel, `/mcp show outsystems` in Copilot CLI, the VS Code MCP view). A config that parses is not a config that loaded.
- **Install recipe** -> run the pasted prompt end to end on that harness, from no configuration to a successful tool call.

Harnesses differ in ways that break otherwise-correct changes: the config key (`servers` vs `mcpServers` vs `mcp_servers`) and its format (JSON vs TOML), the file location, whether tools are enabled by default (Visual Studio disables them), whether an admin policy gates MCP at all (Copilot Business/Enterprise, and Codex on a managed ChatGPT workspace), whether the surface supports plugins at all (the Codex IDE extension does not), and whether the harness synthesizes its own `authenticate` tool or drives OAuth itself. Assume none of these transfer between harnesses without checking.

## Skill docs must stay in lockstep across hosts

This repo ships **six parallel skill documents**:

- `skills/outsystems/SKILL.md` is the Claude Code marketplace skill, consumed when a user runs `claude plugin install outsystems@outsystems`.
- `kiro/outsystems/steering/skill.md` is the Kiro Power steering doc, consumed by Kiro.
- `copilot/skill.md` is the GitHub Copilot skill doc, consumed by GitHub Copilot (VS Code, CLI, or Visual Studio).
- `cursor/skills/outsystems/SKILL.md` is the Cursor skill doc, consumed by Cursor CLI.
- `codex/skills/outsystems/SKILL.md` is the Codex skill doc, consumed after `codex plugin add outsystems@outsystems` and by anyone who copies it into `.agents/skills/outsystems/`.
- `SKILL.md` at the repo root is the top-level fallback skill doc, consumed by hosts that look at the repo root or by anyone reading the repo on GitHub.

All six carry a `## Rules` section that is identical except for one wording drift in the "Go straight to the task" bullet, where root `SKILL.md` says "lazy sign-in" and the other five say "lazy authentication step", and broadly the same `## Tools at a glance`, `### Caveats`, `## Workflows`, and `## Feedback` sections. **Any behavioral change to one MUST be applied to all six.** Updating only one creates a host-specific protection gap. For example, a confirm-before-destructive rule added to `skills/outsystems/SKILL.md` alone protects Claude Code users but leaves Kiro Power, Copilot, Cursor, and Codex users with no protection.

`kiro/outsystems/POWER.md` is a seventh surface, and the grep below covers it only for the shared lead sentence of a rule, not for the rest of a change. It is written for a Kiro operator rather than an agent, so it carries a curated subset rather than a copy: `## Conventions` holds the rules an operator needs to understand, `## Common Workflows` corresponds to `## Workflows`, `## Limitations` to `### Caveats`, `### Tool errors` to the `data.category` rule, and `## Onboarding` and `## Troubleshooting` to `## First use / setup` (which only four docs have) and `## Authenticating`. Only `## Overview` and `## Configuration files` are POWER-only. A behavioral rule lands there when a human debugging Kiro would otherwise be misled, which a rule about diagnosing a failure always is. Keep its lead sentence byte-identical with the six and add it to the grep loop below as a seventh line when the change touches it; the guidance after that sentence legitimately differs in register.

The common failure mode is to edit only `skills/outsystems/SKILL.md` because the marketplace install path points there. Don't.

### Check before opening a PR

After any skill-doc change, grep for two distinctive phrases from the change across all six files and confirm the counts match the expectations below:

```bash
PHRASE="<a distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md codex/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All six counts must be equal for a phrase in `## Rules` or in any other lockstepped section. If they aren't, the change is incomplete and the PR will create a host-specific drift. A phrase that also appears in a host-specific setup or install section legitimately differs, per the setup-flow exception below. Pick one phrase unique to the lockstepped text and expect 6/6, and a second unique to the setup clause and expect 5/6 with root `SKILL.md` at 0 because it has no setup section. State both counts in the PR.

### Exception: setup / installation flows

Setup steps legitimately diverge between the harnesses (Claude Code uses `claude mcp add`, Kiro Power patches `~/.kiro/settings/mcp.json`, GitHub Copilot uses VS Code/Visual Studio settings or Copilot CLI config, Cursor CLI uses `agent mcp` against `~/.cursor/mcp.json`, Codex uses `codex mcp add` against `~/.codex/config.toml`, the root SKILL.md describes the wire-level tool names without prescribing a host). The lockstep rule applies to `## Rules` and to behavioral guidance outside the setup recipe itself, not to host-specific install recipes. `## Authenticating` follows the same exception: each doc describes its own host's sign-in.

### Exception: host-specific affordances

Host-specific UI surfaces (typed shortcuts, hotkeys) live only in the doc for the host that has them. The Claude Code marketplace plugin ships slash commands under `commands/` (declared in `.claude-plugin/plugin.json`'s `commands` key); Kiro Powers do not have an equivalent. So mentions of `/outsystems-feedback` and similar slash-command trigger phrases belong only in `skills/outsystems/SKILL.md`, not in `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, `cursor/skills/outsystems/SKILL.md`, `codex/skills/outsystems/SKILL.md`, or root `SKILL.md`. The underlying *behavior* (what the agent does on the trigger) still has to lockstep across all six docs.

Naming note: slash-command filenames become the command name a user types. Claude Code ships a built-in `/feedback` that routes to Anthropic's issue tracker, so a plugin file named `commands/feedback.md` is shadowed by the host and never fires. Every plugin slash MUST be prefixed with `outsystems-` (`commands/outsystems-feedback.md` → `/outsystems-feedback`) so the host-vs-plugin collision surface is closed by the file name alone.

`commands/` is a Claude-Code-plugin-only directory. There is no Kiro analog, no Copilot analog, no Cursor analog, no Codex analog, and no root analog; do not create one. Behavioral guidance about a command's effect still lands in all six skill docs per the main lockstep rule.

### Manifest version lockstep

Three sets of files, five in total, declare plugin versions and they must stay in sync on every bump:

**Claude:**
- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`

**Cursor:**
- `cursor/.cursor-plugin/plugin.json` -> `version`
- `.cursor-plugin/marketplace.json` -> `plugins[0].version`

**Codex:**
- `codex/.codex-plugin/plugin.json` -> `version`

`claude plugin update outsystems@outsystems` compares the version in `.claude-plugin/plugin.json`. Bumping only `.claude-plugin/marketplace.json` does not trigger an update: the user is told "already at the latest version" and never pulls the new content, even after `claude plugin marketplace update`. Cursor's resolution has not been verified, so treat both Cursor manifests as load-bearing. Always bump all five files in the same commit, keeping the Claude, Cursor, and Codex versions aligned.

Codex is the odd one out on both halves of this. `.agents/plugins/marketplace.json` declares no version at all — it carries only `name`, `source`, `policy`, and `category` per plugin, and Codex reads the version from `codex/.codex-plugin/plugin.json` at install time, which is what `codex plugin list` prints. So there is nothing to bump on the Codex marketplace side, and a Codex marketplace entry that grows a `version` key is a mistake, not a fix. On the other side, `codex plugin add` copies the plugin into `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` and loads it from that cache, so re-installing an unchanged version re-serves the stale copy — bump the version, or append a `+codex.<token>` cachebuster, when iterating locally.
