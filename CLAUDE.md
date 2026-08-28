# CLAUDE.md

Guidance for Claude Code (and other coding agents) when working in this repository.

## Supported harnesses

`README.md` ships an install path per harness. This table is the canonical list of what "all supported harnesses" means. Update it in the same PR that adds or drops a path.

| Harness | Skill doc | How the skill doc arrives | MCP config target | Server key |
| :-- | :-- | :-- | :-- | :-- |
| Claude Code | `skills/outsystems/SKILL.md` | automatic, via `plugin.json`'s `skills` key | user scope, written by `claude mcp add` | n/a |
| Claude Desktop | `skills/outsystems/SKILL.md` | same plugin as Claude Code, installed separately in Desktop's Chat tab (paid plan required) | `claude_desktop_config.json` | `mcpServers` |
| Kiro Chat | `kiro/outsystems/steering/skill.md` | automatic, via the Power's `steering/` directory | `~/.kiro/settings/mcp.json` | `mcpServers` |
| Copilot in VS Code | `copilot/skill.md` | manual copy to `.github/copilot-instructions.md` | `.vscode/mcp.json`, or the user config | `servers` |
| Copilot in CLI | `copilot/skill.md` | manual copy to `.github/copilot-instructions.md` | `~/.copilot/mcp-config.json` | `mcpServers` |
| Copilot in Visual Studio | `copilot/skill.md` | manual download to `.github/copilot-instructions.md` | `<SolutionDir>\.mcp.json`, or `%USERPROFILE%\.mcp.json` | `servers` |
| Cursor App | `cursor/skills/outsystems/SKILL.md` | automatic, via `cursor/.cursor-plugin/plugin.json` | Team Marketplace install (Team/Enterprise plan required) | `mcpServers` |
| Cursor CLI | `cursor/skills/outsystems/SKILL.md` | manual copy to `AGENTS.md` | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project) | `mcpServers` |
| M365 Copilot | n/a | n/a | unsupported: no custom MCP servers | n/a |
| Other assistants | `SKILL.md` (root) | manual fetch, best effort | harness-specific | harness-specific |

Two traps the table encodes:

- **`servers` vs `mcpServers`.** VS Code and Visual Studio read `servers`; Copilot CLI, Kiro, Claude Desktop, and Cursor CLI read `mcpServers`. `copilot/mcp.json` carries both keys so each surface copies the one it needs. Writing the wrong key fails silently: the file still parses and no server appears. (Cursor also has a `.vscode/mcp.json` (IDE-only) that uses `servers`, but the CLI ignores it.)
- **Claude Desktop's plugin requires a paid plan.** On Free, no plugin can be installed, so those users get the tools without the conventions, the confirm-before-destructive rule included. On a paid plan, installing the plugin closes this gap the same way it does for Claude Code.
- **Cursor has dual paths: plugin-based (app) and file-based (CLI).** Cursor App users get the plugin from their Team Marketplace (requires Team/Enterprise plan + team admin approval). Each user then configures via agent setup, which writes `~/.cursor/mcp.json`. Cursor CLI users manually create `~/.cursor/mcp.json` or `.cursor/mcp.json` and use `agent mcp` commands. Both paths use `mcpServers` key. The two skill docs are identical, but only the App path receives one automatically, via the plugin manifest — on the CLI path it is a manual copy to `AGENTS.md`, so a plugin version bump does not reach CLI users at all.

### Validate every change against every supported harness

A change is not done because it works in the harness you happened to test. Before opening a PR, walk the table and account for every row. Exactly three outcomes are acceptable per harness: verified, not applicable with the reason, or a recorded gap with a follow-up. Silence on a row is none of the three.

What "verified" requires depends on what the change touches:

- **Skill-doc wording** -> the lockstep grep below, plus a read of the affected section in each doc that carries it.
- **MCP server config** -> resolve the config on that harness and confirm the server appears with the URL you expect, using whatever the harness offers (`claude mcp list`, Kiro's MCP panel, `/mcp show outsystems` in Copilot CLI, the VS Code MCP view). A config that parses is not a config that loaded.
- **Install recipe** -> run the pasted prompt end to end on that harness, from no configuration to a successful tool call.

Harnesses differ in ways that break otherwise-correct changes: the config key (`servers` vs `mcpServers`), the file location, whether tools are enabled by default (Visual Studio disables them), whether an admin policy gates MCP at all (Copilot Business/Enterprise), and whether the harness synthesizes its own `authenticate` tool or drives OAuth itself. Assume none of these transfer between harnesses without checking.

## Skill docs must stay in lockstep across hosts

This repo ships **five parallel skill documents**:

- `skills/outsystems/SKILL.md` is the Claude Code marketplace skill, consumed when a user runs `claude plugin install outsystems@outsystems`, or when a Claude Desktop user installs the same plugin from the Chat tab.
- `kiro/outsystems/steering/skill.md` is the Kiro Power steering doc, consumed by Kiro.
- `copilot/skill.md` is the GitHub Copilot skill doc, consumed by GitHub Copilot (VS Code, CLI, or Visual Studio).
- `cursor/skills/outsystems/SKILL.md` is the Cursor skill doc, consumed by Cursor CLI.
- `SKILL.md` at the repo root is the top-level fallback skill doc, consumed by hosts that look at the repo root or by anyone reading the repo on GitHub.

All five carry a `## Rules` section that is identical except for one wording drift in the "Go straight to the task" bullet, where root `SKILL.md` says "lazy sign-in" and the other four say "lazy authentication step", and broadly the same `## Tools at a glance`, `### Caveats`, `## Workflows`, and `## Feedback` sections. **Any behavioral change to one MUST be applied to all five.** Updating only one creates a host-specific protection gap. For example, a confirm-before-destructive rule added to `skills/outsystems/SKILL.md` alone protects Claude Code users but leaves Kiro Power, Copilot, and Cursor users with no protection.

`kiro/outsystems/POWER.md` is a sixth surface, and the grep below covers it only for the shared lead sentence of a rule, not for the rest of a change. It is written for a Kiro operator rather than an agent, so it carries a curated subset rather than a copy: `## Conventions` holds the rules an operator needs to understand, `## Common Workflows` corresponds to `## Workflows`, `## Limitations` to `### Caveats`, `### Tool errors` to the `data.category` rule, and `## Onboarding` and `## Troubleshooting` to `## First use / setup` (which only four docs have) and `## Authenticating`. Only `## Overview` and `## Configuration files` are POWER-only. A behavioral rule lands there when a human debugging Kiro would otherwise be misled, which a rule about diagnosing a failure always is. Keep its lead sentence byte-identical with the five and add it to the grep loop below as a sixth line when the change touches it; the guidance after that sentence legitimately differs in register.

The common failure mode is to edit only `skills/outsystems/SKILL.md` because the marketplace install path points there. Don't.

### Check before opening a PR

After any skill-doc change, grep for two distinctive phrases from the change across all five files and confirm the counts match the expectations below:

```bash
PHRASE="<a distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All five counts must be equal for a phrase in `## Rules` or in any other lockstepped section. If they aren't, the change is incomplete and the PR will create a host-specific drift. A phrase that also appears in a host-specific setup or install section legitimately differs, per the setup-flow exception below. Pick one phrase unique to the lockstepped text and expect 5/5, and a second unique to the setup clause and expect 4/5 with root `SKILL.md` at 0 because it has no setup section. State both counts in the PR.

### Exception: setup / installation flows

Setup steps legitimately diverge between the harnesses (Claude Code uses `claude mcp add`, Kiro Power patches `~/.kiro/settings/mcp.json`, GitHub Copilot uses VS Code/Visual Studio settings or Copilot CLI config, the root SKILL.md describes the wire-level tool names without prescribing a host). The lockstep rule applies to `## Rules` and to behavioral guidance outside the setup recipe itself, not to host-specific install recipes.

`skills/outsystems/SKILL.md`'s Claude Desktop first-use subsection inlines the same `npx`/`mcp-remote` config recipe as `README.md`'s Claude Desktop install section (e.g. config paths, Windows variant, PATH caveat, Node/npx prerequisite) because Desktop's Chat tab cannot read the README itself. Keep the two in sync when the recipe changes.

`skills/outsystems/SKILL.md`'s Desktop-facing error-handling paragraphs also point at `README.md`'s `### Reset` heading by absolute URL (`https://github.com/OutSystems/outsystems-mcp#reset`), for the same reason: Desktop's Chat tab cannot read the README to resolve a bare section name. Check those links whenever the Reset heading's text or anchor slug changes.

### Exception: plugin-specific and host-specific affordances

Host-specific UI surfaces (typed shortcuts, hotkeys) live only in the doc for the host that has them; `commands/` is scoped by plugin, not host. The Claude plugin ships slash commands under `commands/` (declared in `.claude-plugin/plugin.json`'s `commands` key); Kiro Powers do not have an equivalent. So mentions of `/outsystems-feedback` and similar slash-command trigger phrases belong only in `skills/outsystems/SKILL.md`, not in `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, `cursor/skills/outsystems/SKILL.md`, or root `SKILL.md`. The underlying *behavior* (what the agent does on the trigger) still has to lockstep across all five docs.

Naming note: slash-command filenames become the command name a user types. Claude Code ships a built-in `/feedback` that routes to Anthropic's issue tracker, so a plugin file named `commands/feedback.md` is shadowed by the host and never fires. Every plugin slash MUST be prefixed with `outsystems-` (`commands/outsystems-feedback.md` → `/outsystems-feedback`) so the host-vs-plugin collision surface is closed by the file name alone.

`commands/` ships via the Claude plugin, same manifest key noted above. There is no Kiro analog, no Copilot analog, no Cursor analog, and no root analog; do not create one. Behavioral guidance about a command's effect still lands in all five skill docs per the main lockstep rule.

The manifest ships `commands/` to any host that installs the plugin, including Claude Desktop, but whether Claude Desktop's Chat tab actually renders and executes a plugin-declared slash command is unverified (see CONTRIBUTING.md's Claude Desktop testing section). Until that is confirmed, `README.md` and `skills/outsystems/SKILL.md` correctly describe `/outsystems-feedback` as Claude-Code-only in user-facing wording; don't change that wording ahead of verification.

### Exception: per-harness Authenticating mechanics

The mechanism prose in `## Authenticating` (whether a harness exposes an agent-callable `authenticate` tool, how each harness's OAuth flow is triggered, and harness-specific error remedies like the callback-port paragraph) is intentionally divergent per harness and exempt from the phrase-count grep. The Reactive paragraph's `tenant_not_allowed` closing sentence is the one exception within Authenticating: it stays byte-identical, once per file, across all five docs, and must be re-grepped at 1x/file across all five whenever a future change touches the Reactive paragraph, per `### Check before opening a PR` above. That grep is change-scoped and operator-run, not a standing automated check, so re-running it is a contributor obligation, not something CI enforces.

Separately, the "if sign-in itself errors" trigger condition is phrased identically in three of the five docs (`skills/outsystems/SKILL.md`, `copilot/skill.md`, root `SKILL.md`), while the other two (`kiro/outsystems/steering/skill.md`, `cursor/skills/outsystems/SKILL.md`) express the same rule as "if sign-in fails"; a wording divergence this exception does not resolve. Treat that phrase as a semantic alignment, not a 5/5 phrase-count case.

### Manifest version lockstep

Two sets of files, four in total, declare plugin versions and they must stay in sync on every bump:

**Claude:**
- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`

**Cursor:**
- `cursor/.cursor-plugin/plugin.json` -> `version`
- `.cursor-plugin/marketplace.json` -> `plugins[0].version`

`claude plugin update outsystems@outsystems` compares the version in `.claude-plugin/plugin.json`. Bumping only `.claude-plugin/marketplace.json` does not trigger an update: the user is told "already at the latest version" and never pulls the new content, even after `claude plugin marketplace update`. Cursor's resolution has not been verified, so treat both Cursor manifests as load-bearing. Always bump all four files (Claude + Cursor pairs) in the same commit, keeping both Claude and Cursor versions aligned.

Claude Desktop installs from the same `.claude-plugin/` manifest pair as Claude Code, and its in-place update resolution is equally unverified; CONTRIBUTING.md's Claude Desktop testing section recommends uninstall/reinstall over trusting an update to have picked up new content.
