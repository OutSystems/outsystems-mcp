# AI PR Review

Every push to a PR triggers an AI code review. This repo is public and
does not share the org-wide credential a centralized, reusable review
workflow elsewhere in the org would need for its cross-repo checkout, so
`ai-review.yml` runs standalone and the critic panel is vendored directly
into `.claude/agents/`.

- `ai-review.yml` - the full workflow: trigger gating, SHA pinning, OIDC
  Bedrock auth, a shell step that prepares the review context, the inline
  review prompt the agent runs against it, and the shell steps that
  validate the agent's payload and post the one review.
- `.claude/agents/*.md` - a critic panel adapted for this repo's shape
  (skill docs, slash commands, plugin manifests - no compiled language,
  no CI to gate on).

## What this repo runs

Narrow, because this repo is not a service. Its content is text an LLM
agent reads (skills, commands, plugin manifests) plus per-harness assets.

Conditional (spawned only when the diff matches the critic's condition,
decided in the prompt before the panel spawns):

- `docs-reviewer` - MD-to-code drift, including `.github/workflows/README.md`
  itself when this workflow or its critics change.
- `consistency-reviewer` **+ agent-facing pack** - skill-doc instruction
  accuracy, cross-harness lockstep, manifest version lockstep, and
  slash-command naming/contract checks. Spawned when the diff touches
  `.claude-plugin/`, `plugin.json`, `marketplace.json`, or any other JSON.
- `error-handling-reviewer` - swallowed errors in skill helpers, if any
  exist in this repo's scripts. Spawned when the diff adds or changes code.
- `simplification-reviewer` **+ context-cost pack** - complexity cost of
  helpers, plus the context cost a skill doc or command body spends on
  every agent that reads it. Spawned when the diff adds or changes code.

Not run at all: `security-reviewer`, `test-reviewer`, `robustness-reviewer`,
`architecture-reviewer`, `compliance-reviewer`. The repo ships no service
code: no test suite, no deploy artifact or ring, no module-boundary
complexity worth a dedicated pass, and no PRC or threat-model artifacts.
The one privileged surface is `ai-review.yml` itself, whose security
properties are recorded below rather than delegated to a critic that does
not run.

Max 3 review rounds; MUST and SHOULD findings post inline, COULD and
lower collapse into the review body.

## Security properties of the review workflow

The repo holds `AI_REVIEW_AWS_ROLE_ARN` and an OIDC trust relationship.
Both are reachable only from the `ai-review` job, which is also the only
job granted `id-token: write` and `pull-requests: write`; the
workflow-level grant is `contents: read`.

Every GitHub API call happens in a shell step, never in the prompt. The
agent session receives the diff, this bot's own prior reviews and inline
comments (filtered to `github-actions[bot]` at fetch time), and the branch
name, and the checkout does not persist the job token into `.git/config`.
Containment is the tool allowlist, not the environment: the action passes
its whole process environment to the CLI, so the session's env does hold
the Bedrock credentials and a copy of the workflow token, but the session
has no tool that can reach the GitHub API or the network, no `gh`, no MCP
server and no unrestricted shell, so it holds nothing it can spend. The
posting step shares this job and its `pull-requests: write`, so widening
`--allowedTools` toward any network- or `gh`-capable tool restores the
write primitive and requires moving the post into a job of its own. The
one shell grant is `git checkout`, and the context step makes
`.git/config` read-only before the agent runs, because git executes the
program named by repo-local keys such as `core.fsmonitor` and the session
holds `Write` over the workspace. PR text written by a third party
therefore reaches the agent only as diff content, and a base ref that
cannot be resolved posts a notice rather than an empty-diff review that
would read as clean. The agent writes a review payload to a file;
a later shell step validates its shape and posts it with `event` and
`commit_id` set by the workflow, so the bot cannot approve a PR even if
the prompt is subverted, and a crashed agent yields a visible notice
rather than silence.

Two consequences of dropping the untrusted inputs. The review cannot dedup
against human review comments, since those are the untrusted channel and
are no longer fetched, so it may repeat a point a reviewer already made.
And the PR title and body are out of context: the review is bound to the
diff and the branch name.

The vendored critics in `.claude/agents/` run no shell command of their
own: the orchestrator prompt hands each one the prepared diff to `Read`,
so the `git diff <base_sha>...HEAD` their files prescribe is not needed,
and every other verification a critic file prescribes as a shell form
(the lockstep count loop `CLAUDE.md` writes as a `for`/`grep -c` loop is
the one instance) is served by `Grep` and `Read`. `git checkout` is the
only shell grant, for the simplification critic's edit-and-revert cycle.
A critic file that needs any other shell form needs the matching grant
added in the same change; without it that critic is denied inside its own
subagent, which degrades the review silently instead of failing the job.

## Required repo configuration

Set once, at the repo level:

| Kind | Name | Value / example |
|---|---|---|
| secret | `AI_REVIEW_AWS_ROLE_ARN` | `arn:aws:iam::<acct>:role/gha-ai-review-bedrock` |
| variable | `AI_REVIEW_AWS_REGION` | `us-east-1` |
| variable | `AI_REVIEW_BEDROCK_MODEL` | `us.anthropic.claude-sonnet-4-6` |

The IAM role's trust policy must include a subject condition allowing
`repo:OutSystems/outsystems-mcp:*`.

## Re-running

- Push a new commit - runs automatically.
- `workflow_dispatch` from the Actions UI, given the PR number and the
  exact head SHA to review.
- Comment `/ai-review <40-char sha>` on the PR. Requires OWNER, MEMBER,
  or COLLABORATOR author association.

## Skipping

Apply the `skip-ai-review` label to a PR before pushing. Removing the
label does not re-engage the review on its own; push again or use one of
the re-run methods above.
