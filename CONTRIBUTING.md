# Contributing to OutSystems MCP

## Overview

This is a distribution-only repository. It packages the OutSystems MCP integration for multiple AI assistant harnesses — Claude Code (via a plugin), Claude Desktop (via the same plugin, installed separately via Desktop's plugin-install flow), Kiro (via a Power), GitHub Copilot (via mcp.json + skill doc), and Cursor (via a plugin for the app, CLI support via mcp.json) — plus a generic `SKILL.md` for other harnesses. The MCP server itself is hosted by OutSystems and is not part of this repo. The deliverables here are the manifests and markdown files under `.claude-plugin/`, `.cursor-plugin/`, `kiro/`, `copilot/`, `cursor/`, `commands/`, and `skills/`. There is no compiled artifact and no build step.

## Prerequisites

- Git.
- At least one of the supported harnesses installed locally. Rows you cannot verify are recorded as gaps with a follow-up per the PR checklist, not skipped silently:
  - **Claude Code** (any recent version) for plugin/skill changes.
  - **Claude Desktop** for MCP config changes and, on a paid plan, plugin/skill-content changes. Verifying skill content additionally requires installing the plugin via Desktop's plugin-install flow, since patching `claude_desktop_config.json` alone only wires up the MCP server.
  - **Kiro 0.11.133 or newer** for Power changes.
  - **Microsoft Copilot** (Business or Enterprise plan with MCP servers policy enabled) for Copilot changes.
  - **Cursor App** (Team/Enterprise plan with team admin access) OR **Cursor CLI** (all plans) for Cursor changes.
- An OutSystems tenant you can authenticate against (e.g. `mycompany.outsystems.dev`) and that is enabled for the MCP server, for end-to-end verification. Authenticating is not sufficient: a tenant outside the server-side allowlist rejects every tool call.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/OutSystems/outsystems-mcp.git
cd outsystems-mcp
```

There is nothing to install or build. The files under `.claude-plugin/`, `.cursor-plugin/`, `kiro/`, `copilot/`, `cursor/`, `commands/`, and `skills/` are the source of truth.

## Repository Structure

```
.claude-plugin/
  marketplace.json        # Claude Code marketplace manifest (lists the plugin)
  plugin.json             # Claude Code plugin manifest (name, version, skills dir, commands dir)
.cursor-plugin/
  marketplace.json        # Cursor marketplace manifest (lists the plugin)
commands/
  outsystems-feedback.md    # Slash command shipped by the Claude plugin
copilot/
  mcp.json                # Copilot MCP server configuration
  skill.md                # Agent guidance for Copilot
cursor/
  .cursor-plugin/
    plugin.json           # Cursor plugin manifest (name, version, skills dir)
  mcp.json                # Cursor CLI MCP server configuration
  README.md               # Cursor install instructions (plugin + CLI)
  skills/
    outsystems/
      SKILL.md            # Agent guidance loaded by Cursor plugin
kiro/
  outsystems/
    POWER.md              # User-facing Kiro Power manifest (onboarding + troubleshooting)
    icon.png              # Logo shown in Kiro's Powers UI
    steering/
      skill.md            # Agent steering content loaded into Kiro Chat
skills/
  outsystems/
    SKILL.md              # Agent-facing skill loaded by the Claude Code plugin
SKILL.md                  # Generic skill content for other harnesses
README.md                 # Install instructions for each supported harness
```

All five skill documents overlap in intent (they all describe the same MCP tools and conventions):
- `skills/outsystems/SKILL.md` (Claude Code, and Claude Desktop via the same plugin)
- `cursor/skills/outsystems/SKILL.md` (Cursor)
- `kiro/outsystems/steering/skill.md` (Kiro)
- `copilot/skill.md` (GitHub Copilot)
- `SKILL.md` (root, generic)

Keep them aligned when changing tool semantics. `kiro/outsystems/POWER.md` carries the same conventions for Kiro operators under `## Conventions`; keep it aligned too. See CLAUDE.md for the lockstep grep check to verify alignment before opening a PR.

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
2. Make your changes. If you touch tool semantics, update every place that documents them (`skills/outsystems/SKILL.md`, `kiro/outsystems/steering/skill.md`, `copilot/skill.md`, `cursor/skills/outsystems/SKILL.md`, and the root `SKILL.md`) so they stay aligned. `kiro/outsystems/POWER.md` carries the same conventions under `## Conventions`; update it too when a rule changes.
3. Open a PR targeting `main`.
4. Account for every supported harness in the CLAUDE.md table, each one verified, not applicable with the reason, or a recorded gap with a follow-up, and record the outcomes in the PR body (see "Testing" below).
5. After review and merge, the version bump goes out as the next release (see [Versioning and Releases](#versioning-and-releases)).

## Testing

There is no automated test suite. Verify changes manually, accounting for every harness in the CLAUDE.md table as step 4 above requires.

### Claude Code (plugin + skills)

Install the local checkout as a marketplace, then install the plugin:

```bash
claude plugin marketplace add ~/path/to/outsystems-mcp
claude plugin install outsystems@outsystems
```

Restart Claude Code, register the MCP server with `claude mcp add` (see the `README.md` install snippet), and run an OutSystems-related prompt end-to-end (e.g. `app_list` followed by `mentor_start` → poll → `publish_start`).

### Claude Desktop

This full sequence — the branch-targeting check, the Fallback default-branch swap, and the Verification steps below — applies to changes that touch the Desktop install recipe (`README.md`'s Claude Desktop section or `skills/outsystems/SKILL.md`'s Desktop subsection), i.e. `CLAUDE.md`'s "Install recipe" verification tier. For skill-doc wording changes outside the setup recipe, `CLAUDE.md`'s lighter "Skill-doc wording" tier applies instead (the lockstep grep plus a read of the affected section), and this section is not required.

Before you start, confirm two prerequisites: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` carry the version you expect (an unbumped version risks leaving testers on previously installed content rather than on your branch; if Desktop's plugin panel shows a currently-installed version, uninstall and reinstall rather than relying on an in-place update to have picked up the new content), and your Desktop client is one where plugins are not org-disabled — an Enterprise admin may restrict or disable plugin installs on a paid plan, per `README.md`'s troubleshooting table. If your org disables them, run this section from a personal/non-managed account or a colleague's org that allows plugins.

**Branch-targeting check (once per contributor):** open Claude Desktop's plugin-install flow and work down this list until one applies, then use that path for every test cycle below. Whichever option ends up applying below, first note the exact menu/panel names and button labels Desktop shows, so the generic wording in `README.md` and above can eventually name them instead of describing the surface generically.

1. **Local filesystem path** — the same zero-exposure mechanism the Claude Code recipe above uses (`claude plugin marketplace add ~/path/to/outsystems-mcp`). If Desktop's install flow accepts a local path, use it and skip everything else in this subsection, including the fallback below.
2. **An arbitrary owner/repo.** If Desktop's marketplace-add accepts any GitHub owner/repo rather than just this org's, push your branch to your own fork and install from `<you>/outsystems-mcp` at that branch. This needs zero admin rights on the shared repo, zero exposure of an unreviewed branch on the public repo, and no revert step, since it's your own fork. If Desktop can't target a specific branch/ref at all, set your fork's own default branch to your working branch instead — this still needs no admin rights on the shared repo and no revert step, since it's your own fork's default branch, not the shared one's.
3. **A branch/ref on this repo directly.** If Desktop's install flow lets you target a non-default branch/ref on `OutSystems/outsystems-mcp`, use that.
4. If none of the above are available **and you have GitHub admin/maintainer rights on this repo**, fall back to the bounded default-branch swap below — read its security cost first.
5. Otherwise (none of options 1-3 available, and no admin rights on this repo), stop and record Claude Desktop as a gap in the PR body, naming which options your Desktop client did not offer — that information is itself useful for whoever picks this up next.

#### Fallback: bounded default-branch swap

Only reach for this when Desktop's plugin-install flow supports none of options 1 through 3 above. It requires GitHub admin/maintainer rights on the shared repo, same as any admin-gated step here, and it has a real security cost that the other options don't: `main`'s branch-protection ruleset (force-push and deletion protection) targets the symbolic `~DEFAULT_BRANCH` ref rather than the literal `main` ref, so swapping the default branch swaps which branch the ruleset protects, leaving `main` unprotected for the swap's duration. Swapping the default branch also means the public `OutSystems/outsystems-mcp` marketplace serves your unreviewed branch content as the published plugin to any user who adds or refreshes it during that window — including anyone already on the marketplace who runs `claude plugin marketplace update outsystems` or Desktop's refresh, which `README.md`'s reset step recommends, not just your own test session — state this exposure, not only the ruleset one, in the PR.

This procedure covers exactly one install-then-revert cycle. It does not cover a second install later in the same test session; see Verification step 1 below for how the two fit together.

**Every exit from this section, whether from this swap or from the Verification steps below, success or failure, must: (1) confirm the branch-protection ruleset still targets `main` — fix it immediately if it doesn't, escalating to a repo admin if it won't restore; (2) run Teardown (the closing paragraph of Verification steps below) to restore local state.**

If the install fails, revert immediately before doing anything else, including before debugging — do not leave this open while troubleshooting, then apply the two closing rules above. If the install succeeds, complete the content-confirmation step below first, then revert; don't linger past that one check, then apply the two closing rules above.

Reverting too early carries its own risk: if you revert before Desktop has actually pulled the plugin's skill content from your branch, every verification step you run afterward silently tests `main`'s content instead of the branch under test. Confirm the installed plugin content reflects your branch (e.g. check for wording your branch introduced) before you revert, not just that the install click succeeded.

1. Temporarily set your branch as the repo's default branch on GitHub.
2. Install the plugin from Desktop's install flow.
3. Confirm the installed content is your branch's — check for one piece of wording your branch introduced (a phrase unique to your change), not a general read — before doing anything else. If the check fails, the install picked up stale content rather than your branch — uninstall and reinstall the plugin rather than relying on an in-place update, and re-check. If a second attempt still shows `main`'s content, revert the default branch now and record Claude Desktop as a gap — see the two closing rules above.
4. Revert the default branch back to `main` immediately — the very next action, not something deferred until verification finishes or a failure is debugged.
5. Confirm the branch-protection ruleset reports `main` as its target again. If it does not, `main` is still unprotected: fix the ruleset target before doing anything else, and if you cannot, escalate to a repo admin immediately and say so in the PR.
6. Run Teardown (the closing paragraph of Verification steps below) to restore local state.

State the exposure and its actual duration in the PR.

#### Verification steps

1. **Save your current state, then install.** Save a copy of `claude_desktop_config.json` before you start; if it already carries an `outsystems` entry from a prior test cycle, remove that entry — step 3 drives the setup recipe from a fresh state and has nothing to exercise otherwise. Every install path above registers a marketplace named `outsystems` (it's the name in `.claude-plugin/marketplace.json`, fixed regardless of source), so also remove any pre-existing `outsystems` marketplace registration first, to avoid resolving to stale content.

   If you used the Fallback default-branch swap above, that install already satisfies this step: skip the install-and-check below and resume at step 2, unless step 4's second pass turns out to be needed, in which case repeat the full swap procedure (steps 1-6 in the Fallback subsection) as a second bounded exposure window, stated separately in the PR, rather than reinstalling against the reverted `main`.

   Otherwise, install the plugin via whichever path above applies, and confirm the installed content is your branch's — check for wording your branch introduced — before proceeding. If the check fails, uninstall and reinstall the plugin rather than relying on an in-place update, and re-check. If a second attempt still shows stale content, stop and record Claude Desktop as a gap — see the two closing rules above. Restart Desktop.

   The plugin delivers the skill doc and slash commands only — `.claude-plugin/plugin.json` declares no `mcpServers` block — so a plugin-only install genuinely has no `outsystems` entry; that's by design, not a bug to fix by adding one.
2. In the Chat tab, ask an OutSystems-related question. If the agent shows zero awareness of any OutSystems-specific behavior at all — no tenant-hostname prompt, no citation of setup instructions, nothing recognizable as skill content — treat this as a suspected blocking finding, to be confirmed once steps 3 and 5 below have run: if the agent also fails to run the Desktop setup subsection in step 3 and fails to apply `## Rules` in step 5, the finding is confirmed. A confirmed finding falsifies the `CLAUDE.md` table's Claude Desktop row and `README.md`'s "delivers the same conventions doc" claim: do not merge either claim until this is resolved, and apply the two closing rules above regardless of outcome.
3. Let the agent drive `skills/outsystems/SKILL.md`'s "For Claude Desktop Users (Manual Config)" subsection end-to-end from a fresh state (tenant prompt, config patch, restart instruction, OAuth sign-in). This is what certifies the skill doc's own Desktop recipe works, not just that Desktop received the plugin. If the agent surfaces the skill but the recipe misleads it, note the specific step and treat it as a doc gap to fix. If the agent cannot run `npx` or read/write `claude_desktop_config.json` at all, do not treat it as a doc gap — it is a harness-capability limit, and it also invalidates `README.md`'s own Desktop paste-prompt recipe (which demands the same capabilities). Record it as a blocking finding, then complete the config edit by hand and continue with steps 5-8; step 4 has its own capability-limited branch below.
4. **Second pass, README-documented order.** Uninstall the plugin and remove the `outsystems` config entry again. Wire the MCP server using `README.md`'s Claude Desktop paste prompt, but with an intentionally broken `command` path (e.g. point it at a nonexistent binary) so the server is configured but failing to connect. A genuinely working server proves nothing here: `## First use / setup`'s entry condition (tools not visible / connection errors) is already false once a server is configured and connected, so the skip-precondition this step exists to test is never actually exercised. Restart Desktop, then reinstall the plugin and restart again. Ask the same kind of OutSystems question. Confirm the skill recognizes the existing (if broken) config and does not re-run its from-scratch setup recipe — this exercises the order `README.md` actually documents (server wired first, plugin installed after), the inverse of steps 1-3 above. If step 3 recorded a harness-capability limit, hand-complete this config edit (with the intentionally broken `command`) yourself too, and test only this recognizes-already-configured half — do not attempt the README paste-prompt through the agent. Gaps found here are Desktop-setup-recipe gaps; fix and record per step 8 below.
5. Confirm the skill's `## Rules` are in effect in the Chat tab: using a disposable/scratch tenant, trigger a destructive-tenant-operation prompt and observe the confirm-before-destructive behavior. If the agent proceeds without confirming, the plugin is delivering the skill doc but Desktop isn't applying its Rules — that falsifies `README.md`'s confirm-before-destructive claim and the `CLAUDE.md` table's Claude Desktop row. Treat this as a confirmed blocking finding (not a lockstep-grep gap; the `## Rules` text is present, the host isn't honoring it), apply the two closing rules above, and do not merge those claims until it's resolved.
6. **One-time, not a per-change check:** test whether `/outsystems-feedback` renders in the Chat tab. Record the result either way — a positive result means the Claude-Code-only wording in `README.md` and `skills/outsystems/SKILL.md` can be revisited (see `CLAUDE.md`'s plugin-affordance exception); a negative result confirms the current wording is still correct. If it renders, also confirm `commands/outsystems-feedback.md`'s `AskUserQuestion`-driven flow actually renders for a plugin running inside Desktop.
7. **Restart-behavior observation (once, not a per-change check):** trigger an auth error mid-session (or simulate one) and observe what a Desktop quit-and-restart does to the `mcp-remote` proxy registration. Record the observed behavior once, in the PR body.
8. If step 3 or step 4 surfaced a gap in the Desktop setup recipe itself, fix it in both `skills/outsystems/SKILL.md`'s Desktop subsection and `README.md`'s Claude Desktop install section (per `CLAUDE.md`'s README-SKILL sync note; setup recipes are exempt from the lockstep grep, so the grep will not catch this), and state both edits in the PR. If any step surfaced a gap in `## Rules` or another lockstepped section, re-run the lockstep grep from `CLAUDE.md` across all five docs before merging.

**Teardown.** Uninstall the test plugin, then reinstall your production `outsystems` plugin if you had one, re-adding your production `outsystems` marketplace registration first if this test removed it. Restore your saved `claude_desktop_config.json`; if the file didn't exist before you started, delete it rather than leaving the test's `outsystems` entry behind.

Record the outcome (verified, gap, or not applicable with reason) in the PR body.

### Kiro (Power)

Point a local registry file at your checkout (Option A in `kiro/outsystems/POWER.md`), restart Kiro, and run an OutSystems-related prompt in Kiro Chat. Verify the agent walks through the tenant prompt and OAuth flow on first use, and that the Power appears in Kiro's Powers UI.

### GitHub Copilot (VS Code, CLI, or Visual Studio)

Point your local GitHub Copilot installation at the `copilot/mcp.json` file (for VS Code / Visual Studio user config or Copilot CLI config), restart the application or reload the MCP servers, and run an OutSystems-related prompt end-to-end. Verify the agent completes a full task such as listing applications, starting an edit session, or publishing an app.

### Cursor App (Plugin)

Before you start, confirm `cursor/.cursor-plugin/plugin.json` and `.cursor-plugin/marketplace.json` carry the version you expect and match the Claude pair under [Versioning and Releases](#versioning-and-releases). An unbumped version risks leaving testers on previously installed content rather than on your branch.

1. For a Team/Enterprise plan, team admin imports the plugin to the Team Marketplace:
   - Temporarily set your branch as the default branch (or use the PR merge branch if available)
   - Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → **Import from Repo**
   - Repo: `OutSystems/outsystems-mcp`, Branch: your test branch
   - Review the `outsystems` plugin and save it **Default On** — deliberately *not* Required, unlike the production guidance in `README.md` and `cursor/README.md`. Required is the right default for a released version; here you are pushing an unmerged branch at a live org marketplace, and Required would force it on everyone.
2. Individual user opens Cursor and asks anything OutSystems-related
3. Agent prompts for tenant hostname, configures `~/.cursor/mcp.json`, and completes OAuth
4. Verify the agent completes a full task such as listing applications, starting an edit session, or publishing an app

### Cursor CLI

Copy the `mcpServers.outsystems` block out of `cursor/mcp.json` — the block only, never the whole file, which opens with a `TEMPLATE ONLY - this is not your MCP config` comment that has no business inside a real config — into `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project), under the `mcpServers` key and with no `type` field. Run:
1. `agent mcp list` to verify `outsystems` is registered
2. `agent mcp enable outsystems` if it shows "needs approval"
3. `agent mcp login outsystems` to trigger OAuth sign-in
4. Save `cursor/skills/outsystems/SKILL.md` to `AGENTS.md` in the test workspace root. Nothing above creates it, and step 5 has nothing to verify without it.
5. Run an OutSystems-related prompt end-to-end in a new agent session. Verify the agent completes a full task such as listing applications, starting an edit session, or publishing an app. Also verify that `AGENTS.md` is properly loaded and the conventions are applied.

### M365 Copilot

Never applicable, because it does not support custom MCP servers, so neither the server nor the skill content reaches it.

### Generic harnesses

For changes to the root `SKILL.md`, fetch it the way the install snippet does (`curl https://raw.githubusercontent.com/...`) and confirm it parses as plain markdown and doesn't reference Claude-Code-specific, Kiro-specific, Copilot-specific, or Cursor-specific affordances.

## Code Standards

- **JSON manifests** (`marketplace.json`, `plugin.json`): two-space indent, trailing newline, sorted alphabetically only where it doesn't reorder a meaningful sequence (e.g. plugin entries in `marketplace.json` should keep listing order).
- **Markdown** (`SKILL.md`, `POWER.md`, skill files, `README.md`): one sentence per concept; prefer short paragraphs over deep heading nesting. Code fences need a language tag.
- **No internal references** in any file shipped to users: no stage hostnames, no internal Jira projects, no team-internal jargon. The repo is public — assume an external developer is reading.

## Versioning and Releases

Version lives in four places and must stay in sync:

**Claude:**
- `.claude-plugin/plugin.json` → `version`
- `.claude-plugin/marketplace.json` → `plugins[0].version`

**Cursor:**
- `cursor/.cursor-plugin/plugin.json` → `version`
- `.cursor-plugin/marketplace.json` → `plugins[0].version`

Bump all four in a single commit using the `chore(plugin):` scope (e.g. `chore(plugin): bump version 0.5.0 -> 0.6.0`).

For Claude Code, `claude plugin update` compares the version in `.claude-plugin/plugin.json`. Leave that one behind and users are told "already at the latest version" and never pull the new content, even after `claude plugin marketplace update`. The marketplace entry is what a user browses before installing, so keeping it in step matters for what a release advertises rather than for whether the update fires.

Cursor's resolution has not been verified the same way. Bump both Cursor manifests together and do not rely on one covering for the other.

Claude Desktop installs from the same `.claude-plugin/` pair as Claude Code, but its in-place update resolution has not been verified either; when testing a bump on Desktop, uninstall and reinstall rather than trusting an update to have picked up new content (see the Claude Desktop testing section above).

Versioning follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — breaking change to install instructions, file layout, or required harness version.
- **MINOR** — new skill content, new workflows documented, new install path for an additional harness.
- **PATCH** — fixes and clarifications that don't change how a user installs or invokes the integration.

There is no automated release pipeline yet. After the version-bump commit lands on `main`, users pick up the change on their next `claude plugin install`, Claude Desktop plugin install or reinstall, Cursor Team Marketplace refresh, or Kiro Power re-fetch.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
