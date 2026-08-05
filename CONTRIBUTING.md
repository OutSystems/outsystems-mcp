# Contributing to OutSystems MCP

## Overview

This is a distribution-only repository. It packages the OutSystems MCP integration for multiple AI assistant harnesses — Claude Code (via a plugin), Kiro (via a Power), GitHub Copilot (via mcp.json), and Cursor (via mcp.json) — plus a generic `SKILL.md` for other harnesses. The MCP server itself is hosted by OutSystems and is not part of this repo. The deliverables here are the manifests and markdown files under `.claude-plugin/`, `kiro/`, `copilot/`, `cursor/`, and `skills/`. There is no compiled artifact and no build step.

## Prerequisites

- Git.
- At least one of the supported harnesses installed locally, to manually verify changes:
  - **Claude Code** (any recent version) for plugin/skill changes.
  - **Kiro 0.11.133 or newer** for Power changes.
  - **Microsoft Copilot** (Business or Enterprise plan with MCP servers policy enabled) for Copilot changes.
  - **Cursor CLI** (with `agent` commands available) for Cursor changes.
- An OutSystems tenant you can authenticate against (e.g. `mycompany.outsystems.dev`) for end-to-end verification.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/OutSystems/outsystems-mcp.git
cd outsystems-mcp
```

There is nothing to install or build. The files under `.claude-plugin/`, `kiro/`, `copilot/`, `cursor/`, and `skills/` are the source of truth.

## Repository Structure

```
.claude-plugin/
  marketplace.json        # Claude Code marketplace manifest (lists the plugin)
  plugin.json             # Claude Code plugin manifest (name, version, skills dir)
copilot/
  mcp.json                # Copilot MCP server configuration
  skill.md                # Agent guidance for Copilot
cursor/
  mcp.json                # Cursor MCP server configuration
  skill.md                # Agent guidance for Cursor
kiro/
  outsystems/
    POWER.md              # User-facing Kiro Power manifest (onboarding + troubleshooting)
    icon.png              # Logo shown in Kiro's Powers UI
    steering/
      skill.md            # Agent steering content loaded into Kiro Chat
skills/
  outsystems/
    SKILL.md              # Agent-facing skill loaded by the Claude Code plugin
SKILL.md                  # Generic skill content for non-Claude-Code / non-Kiro / non-Copilot / non-Cursor harnesses
README.md                 # Install instructions for each supported harness
```

`skills/outsystems/SKILL.md`, `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, and the root `SKILL.md` overlap heavily in intent (they all describe the same MCP tools and conventions). Keep them aligned when changing tool semantics, but each is tailored to its harness — don't blindly copy edits across them.

## Development Workflow

### Branch naming

Branches follow `<type>/<short-description>` — e.g. `docs/rename-to-outsystems-mcp`, `feat/host-based-tenant-url`, `chore/bare-stamp-hostname`. `type` is one of `feat`, `fix`, `docs`, `chore`, `skills`, `refactor`.

### Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), with a scope tag identifying the affected surface:

```
docs(README): switch install URLs to host-based tenant URL
docs(skill): neutralize Claude-Code-specific prefix in root SKILL
docs(POWER): use *.outsystems.dev example for network-access bullet
fix(power): mentor async, optional iconUrl, anonymous clone
feat(kiro): drop per-Power mcp.json, write MCP URL to user settings only
chore(plugin): bump version 0.5.0 -> 0.6.0
skills(mentor): switch references to async mentor primitive
```

Common scopes: `plugin`, `power`, `kiro`, `skill`, `mentor`, `README`, `POWER`.

### Pull requests

1. Create a branch from `main`.
2. Make your changes. If you touch tool semantics, update every place that documents them (`skills/outsystems/SKILL.md`, `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, and the root `SKILL.md`) so they stay aligned.
3. Open a PR targeting `main`.
4. Verify the change in at least one supported harness (see "Testing" below) and describe what you tested in the PR body.
5. After review and merge, the version bump goes out as the next release (see "Releases").

## Testing

There is no automated test suite. Verify changes manually in the harness(es) you touched.

### Claude Code (plugin + skills)

Install the local checkout as a marketplace, then install the plugin:

```bash
claude plugin marketplace add ~/path/to/outsystems-mcp
claude plugin install outsystems@outsystems
```

Restart Claude Code, register the MCP server with `claude mcp add` (see the `README.md` install snippet), and run an OutSystems-related prompt end-to-end (e.g. `app_list` followed by `mentor_start` → poll → `publish_start`).

### Kiro (Power)

Point a local registry file at your checkout (Option A in `kiro/outsystems/POWER.md`), restart Kiro, and run an OutSystems-related prompt in Kiro Chat. Verify the agent walks through the tenant prompt and OAuth flow on first use, and that the Power appears in Kiro's Powers UI.

### GitHub Copilot (VS Code, CLI, or Visual Studio)

Point your local GitHub Copilot installation at the `copilot/mcp.json` file (for VS Code / Visual Studio user config or Copilot CLI config), restart the application or reload the MCP servers, and run an OutSystems-related prompt end-to-end. Verify the agent completes a full task such as listing applications, starting an edit session, or publishing an app.

### Cursor CLI

Point your local Cursor CLI at the `cursor/mcp.json` file (copy to `~/.cursor/mcp.json` global config or `.cursor/mcp.json` project config, using the `mcpServers` key without `type` field). Run:
1. `agent mcp list` to verify `outsystems` is registered
2. `agent mcp enable outsystems` if it shows "needs approval"
3. `agent mcp login outsystems` to trigger OAuth sign-in
4. Run an OutSystems-related prompt end-to-end in a new agent session. Verify the agent completes a full task such as listing applications, starting an edit session, or publishing an app. Also verify that `.cursorrules` is properly loaded and the conventions are applied.

### Generic harnesses

For changes to the root `SKILL.md`, fetch it the way the install snippet does (`curl https://raw.githubusercontent.com/...`) and confirm it parses as plain markdown and doesn't reference Claude-Code-specific, Kiro-specific, Copilot-specific, or Cursor-specific affordances.

## Code Standards

- **JSON manifests** (`marketplace.json`, `plugin.json`): two-space indent, trailing newline, sorted alphabetically only where it doesn't reorder a meaningful sequence (e.g. plugin entries in `marketplace.json` should keep listing order).
- **Markdown** (`SKILL.md`, `POWER.md`, skill files, `README.md`): one sentence per concept; prefer short paragraphs over deep heading nesting. Code fences need a language tag.
- **No internal references** in any file shipped to users: no stage hostnames, no internal Jira projects, no team-internal jargon. The repo is public — assume an external developer is reading.

## Versioning and Releases

Version lives in two places and must stay in sync:

- `.claude-plugin/marketplace.json` → `plugins[0].version`
- `.claude-plugin/plugin.json` → `version`

Bump both in a single commit using the `chore(plugin):` scope (e.g. `chore(plugin): bump version 0.5.0 -> 0.6.0`).

Versioning follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — breaking change to install instructions, file layout, or required harness version.
- **MINOR** — new skill content, new workflows documented, new install path for an additional harness.
- **PATCH** — fixes and clarifications that don't change how a user installs or invokes the integration.

There is no automated release pipeline yet. After the version-bump commit lands on `main`, users pick up the change on their next `claude plugin install` / Kiro Power re-fetch.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
