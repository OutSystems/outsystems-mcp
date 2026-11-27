# OutSystems Legacy Modernization (plugin)

Skills, commands and subagent roles for modernizing legacy applications onto
OutSystems Developer Cloud (ODC). The agent extracts the requirements from the
legacy sources, then designs, generates and verifies the replacement app on your
tenant through the OutSystems MCP server, and closes with the client documents and a
test pack your team can re-run.

Plugin name: `legacy-modernization`. It ships in the `outsystems` marketplace next
to the `outsystems` plugin, and it depends on that plugin's MCP server: it ships
no MCP server, tenant URL or token of its own.

## Limited availability

Legacy modernization is in limited availability until general availability. Access is
per tenant: the `modernize_*` tools appear only on tenants that have it. Every command
and skill in this plugin checks for them first, except the overview (`/how-it-works` and
the `legacy-modernization-overview` skill), which only explains the toolkit and says it is
in limited availability. On any other tenant the agent says
"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access." and stops. To request access, contact your OutSystems team.

## Legacy stacks

Extraction needs your tenant enabled for it. On an enabled tenant it currently reads:

- Lotus Notes / Domino (`.dxl`)
- Unisys AB Suite (`.pmodel` exports)
- MS Access
- IBM AS/400 (DDS, RPG and CL source), including CA 2E / Synon model exports
- COBOL
- Java
- .NET
- Node.js

## Commands

| Command | What it does |
|---|---|
| `/legacy-modernization:extract-requirements` | Extracts a requirements spec collection from legacy sources through the OutSystems MCP `modernize_*` tools, then hands off to `/workflow-legacy-app`. |
| `/legacy-modernization:generate-design-options` | The design half of the migration on its own: about three design options, a pause for your pick, then the design gate on the picked one. Builds nothing. |
| `/legacy-modernization:workflow-legacy-app` | Builds the replacement app from that spec: design, Mentor build in per-chunk publishes, review and test gates, and a closing report. |
| `/legacy-modernization:how-it-works` | A one-page overview of the toolkit, or the answer to one question about it. |

## Skills

| Skill | Use it for |
|---|---|
| `legacy-requirements-extraction` | extracting the specs of legacy source code through the `modernize_*` tools |
| `outsystems-handover-docs` | the client Business Specification and Implementation Report pair |
| `outsystems-test-evidence-pack` | a Playwright test evidence pack shipped beside the app |
| `legacy-modernization-overview` | the toolkit overview page behind `/how-it-works` |

The roles also use the general Mentor build skills, which aren't specific to legacy
modernization and ship in the `outsystems` plugin: `outsystems-app-build`,
`outsystems-ui-recipes`, `outsystems-block-editing`, `outsystems-css-theming`,
`outsystems-osui-idioms`, `outsystems-ui-exactness`, `outsystems-figma-design-source` and
`outsystems-auth-and-deploy`. The `designer`, `developer` and `reviewer` roles preload
several of them; when one isn't installed, the role says so instead of guessing its rules.

The six roles under `agents/` (`planner`, `designer`, `developer`, `reviewer`,
`tester`, `reporter`) read their full playbooks from `app/prompts/`. The workflow
step graph and gate policy live in `app/lib/workflows.py` as data; nothing runs it.

## Install

### Claude Code

Install the `outsystems` plugin first (see the repository README), then add this one
from the same marketplace:

```bash
claude plugin install legacy-modernization@outsystems
```

Don't re-run the `outsystems` install command to get here: reinstalling it with
`--config` overwrites the tenant you saved. If you installed an earlier copy of this
plugin from another marketplace, uninstall that copy first: both carry the same
commands and roles.

Start a new session afterwards.

### Cursor App

In your Team Marketplace, import `OutSystems/outsystems-mcp` and enable the
`legacy-modernization` plugin next to `outsystems`.

### Other Agent Skills hosts

The folder follows the [agent-plugins.org 1.0.0](https://agent-plugins.org/specification)
layout for skills. Hosts that load skills from a folder, such as
Codex or Kiro, can copy `skills/*` into their skills directory. They get the skills,
but not the commands or the subagent roles. Copy the `outsystems` plugin's skills the same way.

## Dependencies

| Dependency | Required for | Install |
|---|---|---|
| **OutSystems MCP** | everything: Mentor edits, publish, deploy, the access check | the `outsystems` plugin in this marketplace, or the per-harness recipes in the repository README |
| **A frontier model** | generation | the strongest model your host offers. Smaller models finish too, with more retries and cleanup |
| **Figma MCP** | reading pasted designs, generating design options in Figma | `https://mcp.figma.com/mcp`. Without it the design phase falls back to HTML/CSS mockups, with the same number of options |
| **A way to drive a URL** | drive-testing the published app and taking screenshots | the host's own browser surface first. If the host has none, add the Playwright MCP (`npx @playwright/mcp@latest`, Node 18+). With no surface at all, checks are reported `NOT OBSERVABLE (tooling)`, never silently passed |
| **Node.js 20.12+ and Python 3.8+** | the test evidence pack and its checks | from your platform's usual installer |
| **PDF tooling** (optional) | rendering the handover reports to PDF | Playwright print-to-PDF, or `pandoc`. Without it, reports ship as markdown and say so |
| **Legacy extraction** (`modernize_*` tools on the OutSystems MCP) | `/extract-requirements` | nothing to install: the tools appear once your tenant has access (see Limited availability) |

### If OutSystems MCP is not installed

This plugin does not ship the OutSystems MCP server. With no `outsystems` server
attached, every build and edit command stops. Install the `outsystems` plugin from
this marketplace (or follow the repository README for your harness), sign in, then
start a new session.

If the `modernize_*` tools are missing, check sign-in first (see below). If you are
signed in, in a session started after sign-in, and the tools are still missing, your
tenant doesn't have access yet: legacy modernization is in limited availability, so
contact OutSystems to request it.

### Authorize before you run

- **Attaching a server is not signing in to it.** The OAuth sign-in is a separate
  step, and the OutSystems and Figma servers don't work until it completes.
- **Sign in from an interactive session.** OAuth needs a browser, so a headless run
  cannot complete it. Sign in first, then start the automated run.
- **Then start a new session.** A session that began before sign-in keeps its failed
  connection, so the tools stay missing even after the server is signed in.
- **Check it is the right tenant.** The agent builds on whatever tenant the server
  points at. With more than one OutSystems server attached, tell the agent which one.

On Claude Code, `claude mcp list` is the check: `✔ Connected` means signed in,
`! Needs authentication` means it isn't yet. `/clear` does not start a new session;
exit and start Claude Code again.

## Update

| Host | How |
|---|---|
| Claude Code | `claude plugin marketplace update outsystems`, then `claude plugin update legacy-modernization@outsystems`, then start a new session |
| Cursor App | refresh the Team Marketplace import |
| Folder copies (Codex, Kiro, others) | copy `skills/*` again from the new version |

The extraction skill checks the latest released version in this folder's
`.claude-plugin/plugin.json` and tells you once per run when your copy is older.

## Uninstall

On Claude Code, run `claude plugin uninstall legacy-modernization@outsystems`. It
leaves the `outsystems` plugin and its MCP server in place. On folder-copy hosts,
delete the skill folders you copied.
