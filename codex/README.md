# Codex - OutSystems MCP Plugin

This directory ships the OutSystems MCP plugin for Codex. Codex discovers plugins through a marketplace, so this repo doubles as one: the index lives at [`.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json) in the repo root and points at this directory.

## Which Codex surface supports what

| Surface | Plugins | MCP servers | Skill delivery |
| :-- | :-- | :-- | :-- |
| Codex CLI | yes (`codex plugin`, or `/plugins` in the TUI) | yes (`codex mcp`, `~/.codex/config.toml`) | plugin, or a file under `.agents/skills/` |
| Codex in the ChatGPT desktop app (macOS) | yes (**Plugins** tab) | yes (**Settings > MCP servers**) | plugin, or a file under `.agents/skills/` |
| Codex IDE extension (VS Code) | **no** | yes (gear menu > **MCP servers**) | a file under `.agents/skills/` only |

Two things follow from the table, and both are easy to get wrong:

- **The IDE extension has no plugin support at all.** MCP works there, so the tools appear, but a plugin-delivered skill does not. IDE-extension users need the skill installed as a file, or they get the tools without the conventions — the confirm-before-destructive rule included.
- **All three surfaces share `~/.codex/config.toml`.** MCP servers, marketplace registrations, and per-plugin enable state all live there, so installing from the CLI is what makes the plugin appear in the desktop app too. There is no separate desktop-app install to perform.

**Requires Codex 0.147.0 or newer**, which is when `codex plugin` and skill frontmatter landed; check with `codex --version`. Verified against Codex CLI 0.148.0.

## Install - plugin (CLI and ChatGPT desktop app)

```bash
codex plugin marketplace add OutSystems/outsystems-mcp
codex plugin add outsystems@outsystems
```

`codex plugin marketplace add` also accepts a local path, an HTTPS Git URL, or an SSH Git URL, plus `--ref` to pin a branch or tag and `--sparse` to limit the checkout.

The plugin ships the **skill only**. It cannot ship the MCP server entry: a Codex plugin manifest *can* declare `mcpServers`, but only as a static command or URL, and the OutSystems URL contains the user's tenant hostname. So after installing, ask Codex anything OutSystems-related and the skill drives the rest:

1. The agent asks for your **OutSystems tenant hostname** (e.g. `mycompany.outsystems.dev`).
2. The agent runs `codex mcp add outsystems --url https://<my-tenant>/mcp`, which writes `~/.codex/config.toml`.
3. The agent hands you `codex mcp login outsystems` to run **yourself, in your own terminal**; you complete the OAuth sign-in in the browser.
4. The agent verifies and retries your original request.

Verify at any point with:

```bash
codex plugin list        # outsystems@outsystems -> installed, enabled
codex mcp list           # outsystems -> Status: enabled, and Auth: NOT "Not logged in"
```

Start a new session after installing — bundled skills are picked up at session start.

### Run the sign-in outside the session

`~/.codex/` sits outside the sandbox that Codex applies to commands it runs, so anything writing there is denied with `Operation not permitted`. The two setup commands fail differently, and only one of them tells you:

- `codex mcp add` fails **loudly** — `failed to persist config at ~/.codex/config.toml … Operation not permitted`, non-zero exit. Nothing is half-done; re-run it yourself.
- `codex mcp login` fails **silently**. The OAuth flow is network plus a loopback callback, so the browser sign-in genuinely succeeds and the command prints `Successfully logged in to MCP server 'outsystems'`. Only the token write is denied, and the command doesn't surface that. You find out in the next session, as `The outsystems MCP server requires OAuth reauthentication` and `MCP startup incomplete (failed: outsystems)`.

So run `codex mcp login outsystems` in a plain terminal, and check it stuck with `codex mcp list`. **Read the `Auth` column, not `Status`**: `Status: enabled` only means the server is registered, while `Auth: Not logged in` means no token was stored. A telltale that a command ran sandboxed is `WARNING: proceeding, even though we could not create PATH aliases: Operation not permitted (os error 1)` in its output.

## Install - skill as a file (no plugin)

Use this when you're on the IDE extension, or you'd rather not install a plugin. Register the server the same way (`codex mcp add outsystems --url https://<my-tenant>/mcp`), then place the conventions doc yourself.

Codex discovers skills from `<dir>/.agents/skills/<name>/SKILL.md` in four scopes, all verified on 0.148.0:

| Scope | Location | Use it for |
| :-- | :-- | :-- |
| Repo | `$REPO_ROOT/.agents/skills/`, plus `.agents/skills/` in every directory from the CWD up | scoping the conventions to one project, checked into the repo |
| User | `~/.agents/skills/` | every project you work on, not checked in |
| Admin | `/etc/codex/skills/` | machine- or image-wide defaults |
| System | bundled with Codex | not yours to write |

For the per-user install:

```bash
mkdir -p ~/.agents/skills/outsystems
curl -fsSL https://raw.githubusercontent.com/OutSystems/outsystems-mcp/refs/heads/main/codex/skills/outsystems/SKILL.md \
  -o ~/.agents/skills/outsystems/SKILL.md
```

Copy the file verbatim and keep the YAML frontmatter: Codex decides when to load a skill from the `name` and `description` in that frontmatter, so a doc pasted without it is inert. Skills are picked up on the next session; `~/.codex/skills/<name>/SKILL.md` also still resolves, but `.agents/skills` is the documented path.

`AGENTS.md` is the other option and a worse one here: it is always-on context that costs tokens every turn, where a skill is loaded on demand. Prefer `.agents/skills/`; reach for `AGENTS.md` only if you want the conventions unconditionally in front of the model.

## Free, paid, and managed workspaces

Nothing here requires a paid plan. Codex is available from the Free tier up, and the CLI plugin browser and `codex mcp` work the same on Free, Go, Plus, Pro, and API-key sign-in. That is a real difference from the Cursor App path in this repo, which needs a Team or Enterprise plan and a team admin.

ChatGPT Business, Enterprise, and Edu workspaces are where it changes, because an admin can constrain a managed Codex client through `requirements.toml` (system-wide, cloud-delivered, or MDM). Four controls can each block this install on their own:

- `marketplaces.restrict_to_allowed_sources = true` plus `marketplaces.allowed_sources.*` — `codex plugin marketplace add OutSystems/outsystems-mcp` is refused unless a rule allows this repository (`source = "git"` with the repo URL, or a `host_pattern` covering `github.com`).
- `features.plugins` — pins plugin availability on or off for managed users, regardless of the marketplace.
- `mcp_servers` — an allowlist where **both** the server name and its identity must match. The identity here is the URL, so a rule has to name `https://<tenant>/mcp` exactly (or a matching prefix/regex).
- Workspace plugin controls in ChatGPT admin settings govern the web and desktop surfaces; the CLI installs through its own browser.

The symptom of all four is the same and misleading: the command reports success, or Codex reports falling back to a compatible value, and the server or plugin never appears. When `codex mcp list` and `codex plugin list` disagree with what you just ran on a managed machine, it's policy, not a bad edit.

## Version Alignment

Codex, Cursor, and Claude plugin versions must stay in sync:
- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`
- `cursor/.cursor-plugin/plugin.json` -> `version`
- `.cursor-plugin/marketplace.json` -> `plugins[0].version`
- `codex/.codex-plugin/plugin.json` -> `version`

Update all five together in the same commit when bumping the version. Codex's `.agents/plugins/marketplace.json` carries no version of its own — it resolves the version from the plugin manifest — so there is nothing to bump there.

The version is also what makes a reinstall take effect: `codex plugin add` copies the plugin into `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` and loads it from there, so re-running the install against an unchanged version re-serves the cached copy. Bump the version (or append a `+codex.<token>` cachebuster) when iterating locally.

## Skill Docs Lockstep

The Codex skill doc is `codex/skills/outsystems/SKILL.md`, shipped via `codex/.codex-plugin/plugin.json`'s `skills` key. It must stay synchronized with the other harness skill docs:
- `skills/outsystems/SKILL.md` (Claude Code)
- `kiro/outsystems/steering/skill.md` (Kiro)
- `copilot/skill.md` (GitHub Copilot)
- `cursor/skills/outsystems/SKILL.md` (Cursor)
- `SKILL.md` (root, generic)

All six files carry the same `## Rules`, `## Workflows`, and `## Feedback` sections. Any behavioral change to one must be applied to all six. Setup and Authenticating sections legitimately differ per host.

Use the lockstep grep check before opening a PR:
```bash
PHRASE="<distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md copilot/skill.md cursor/skills/outsystems/SKILL.md codex/skills/outsystems/SKILL.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All counts must be equal.

## Validating a change to this plugin

Codex ships both validators as system skills. Both need `pyyaml`:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py codex
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/outsystems
```

Then confirm the marketplace resolves this directory and the install succeeds:

```bash
codex plugin marketplace add .        # from the repo root
codex plugin list                     # outsystems@outsystems -> <repo>/codex
codex plugin add outsystems@outsystems
```

`codex plugin list` is the check that matters: it prints the path Codex actually resolved from `source.path`, which is relative to the marketplace root (the repo root), not to the marketplace file. A wrong path shows up there and nowhere else. Clean up afterwards so a local checkout doesn't stay wired into your config:

```bash
codex plugin remove outsystems@outsystems
codex plugin marketplace remove outsystems
```
