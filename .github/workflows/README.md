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
- `.github/tests/` - the test suite for this workflow's shell steps and
  for the guarantees its structure makes. See "Tests" below.

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
code: no deploy artifact or ring, no module-boundary complexity worth a
dedicated pass, and no PRC or threat-model artifacts. The one body of
executable content is this workflow's own shell, which has its own suite
under `.github/tests/` rather than a critic seat.
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
name. `.git/config` is not token-free: the checkout runs with
`persist-credentials: false`, but the review action re-adds the job token
to `remote.origin.url` in agent mode, where the session's Read grant can
see it. Containment is the tool allowlist, not the environment: the
action passes its whole process environment to the CLI, so the session's
env does hold the Bedrock credentials and a copy of the workflow token,
but the session has no tool that can reach the GitHub API or the network,
no `gh`, no MCP server and no shell, so it holds nothing it can spend. The
posting step shares this job and its `pull-requests: write`, so widening
`--allowedTools` toward any network- or `gh`-capable tool restores the
write primitive and requires moving the post into a job of its own. The
session holds no shell at all, `git` included: with `Write` in the same
session, any git invocation executes the program named by
`diff.external` or `core.fsmonitor`, out of the repo config, the runner's
global config or a `.git/hooks/` script, so no permission on one of those
files contains it. PR text written by a third party therefore reaches the
agent only as diff content. A base ref that cannot be resolved, and a
head with no diff against a base that did resolve, each post a notice
naming which of the two happened, rather than an empty-diff review that
would read as clean. That route is taken from the context step's outputs,
never from a file in the directory the agent can write. The agent writes
a review payload to a file; a later shell step validates its shape and
posts it with `event` and
`commit_id` set by the workflow, so the bot cannot approve a PR even if
the prompt is subverted, and a crashed agent yields a visible notice
rather than silence. Every notice ends with a hidden
`<!-- ai-review:notice -->` marker, and the next run never takes a
notice's head as the last reviewed one, so the changes at that head still
count as new.

Two consequences of dropping the untrusted inputs. The review cannot dedup
against human review comments, since those are the untrusted channel and
are no longer fetched, so it may repeat a point a reviewer already made.
And the PR title and body are out of context: the review is bound to the
diff and the branch name.

The vendored critics in `.claude/agents/` run no shell command of their
own: the orchestrator prompt hands each one the prepared diff to `Read`,
so the `git diff <base_sha>...HEAD` their files prescribe is not needed,
and the shell forms a critic file still prescribes - the `for`/`grep -c`
lockstep loop from `CLAUDE.md`, plus `simplification-reviewer.md`'s
`wc -c` measurement and its build/lint/test step - are redirected by the
orchestrator prompt to `Grep` and `Read`, or to inspection where this
repo, markdown and JSON with no build system, has nothing to run. The
session holds no shell grant at all, so a critic file that starts
prescribing a shell form needs that override extended in the same change;
without it the critic is denied inside its own subagent, which degrades
the review silently instead of failing the job.

## Tests

```bash
.github/tests/run.sh
```

Needs `bash`, `git`, `jq` and `python3` with PyYAML. Nothing invokes it
automatically: this repo runs no CI beyond the review itself, so run it
before pushing a change to `ai-review.yml`.

The step suites extract the `run:` bodies from the committed workflow and
execute them under the shell Actions gives them, with `gh` and `sleep`
replaced by stubs, so the code under test is the code that ships. The
contract and spec suites read the same committed workflow as data. What
the suites pin down:

- `workflow-contract.test.sh` - the guarantees that live in the
  structure: per-job token scope, an agent allowlist with no shell and
  nothing that reaches the network, a checkout that persists no
  credentials, the step order, and the trigger surface.
- `resolve-step.test.sh` - the per-trigger gate and the five outputs the
  review job runs on, including the branch name.
- `context-step.test.sh` - the files the agent is allowed to read, the
  filtering that keeps third-party text out of them, the delta staying
  inside the diff under review, a notice never standing in for the last
  review, and the degraded inputs that must warn rather than fail the job.
- `payload-step.test.sh` - every payload whose keys reach the API as one
  review, every one that reaches it as the notice instead, and a notice
  route that only the context step's outputs can select. The gate
  checks keys, not value types: an element with the right keys and a
  wrong value type reaches the API, and the post step's fold is what
  keeps its finding.
- `post-step.test.sh` - one review per run, and the two recoveries: a
  rejected payload keeps its findings in the body, a transport failure
  keeps its payload and does not publish twice, and an earlier run's
  review of the same head is not mistaken for this run's.
- `spec_untrusted_input_port.test.sh` - the properties that keep
  untrusted input away from the privileged agent: the comment fetch and
  the review POST are shell steps and not prompt instructions, the tool
  grant keeps `Task` but no shell, `id-token: write`
  is scoped to the `ai-review` job alone, no credential file is written
  on any trigger, and this README does not deny the surface.

A case that needs `gh` behaviour the stub does not have belongs in the
stub, not in a mock of the step: a test that reimplements the step
proves the test.

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

Two of those three run the workflow file you are looking at; the comment
one may not. `issue_comment` carries no ref, so GitHub resolves the
workflow against the default branch, never the PR's version of it, while
`workflow_dispatch` takes an explicit `--ref` and `pull_request` runs the
PR's file. A comment-triggered run on an open PR therefore exercises the
merged workflow, so it cannot confirm or refute a change to this file
that has not landed yet: dispatch that change with `--ref <branch>`, and
read its structural guarantees off `.github/tests/`, which take the
committed file as their input.

Pin a SHA that belongs to the PR. Both manual triggers take the SHA on
trust, so a review posted against a commit from elsewhere in the
repository stays on the PR as a review of a commit it does not contain.
The next run notices and re-reviews in full rather than diffing from it.

## Skipping

Apply the `skip-ai-review` label to a PR before pushing. Removing the
label does not re-engage the review on its own; push again or use one of
the re-run methods above.
