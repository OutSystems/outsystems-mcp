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
comments (filtered to `github-actions[bot]` at fetch time), the branch
name, the list of tracked paths at the head, and an index of the lines at
the head that contain an identifier the diff adds or removes. The action passes its whole process environment to the CLI, so the
session's env holds the Bedrock credentials and a copy of the workflow
token, and the checkout's `persist-credentials: false` does not keep the
token out of `.git/config`: the review action re-adds it to
`remote.origin.url` in agent mode. Containment is the session's tool
grants.

- **Four built-in tools, and nothing else.** `--tools` limits the
  session and its subagents to `Task`, `Read`, `Edit` and `Write`. The
  permission mode alone does not keep a built-in out: `EnterWorktree`
  runs `git worktree add` in the workspace with no allow rule, creating a
  branch and writing `.git/worktrees/`, so the set is restricted rather
  than trimmed with deny rules that would have to track every CLI
  release.
- **No tool that reaches the network or runs a program.** No `gh`, no MCP
  server, no WebFetch and no shell grant, `git` included: with any write
  in the same session, a git invocation executes the program named by
  `diff.external` or `core.fsmonitor`, out of the repo config, the
  runner's global config or a `.git/hooks/` script. The posting step
  shares this job and its `pull-requests: write`, so widening the grants
  toward any network- or `gh`-capable tool restores the write primitive
  and requires moving the post into a job of its own.
- **File tools scoped by path.** A bare `Read`, `Write` or `Edit` allow
  rule approves that tool on every path on the runner. The grants are
  instead `Read` on the workspace and the context directory
  (`$RUNNER_TEMP/ai-review`), and `Edit`, which governs every
  file-writing tool, on the context directory alone.
  The session runs in `dontAsk` mode, so a call no rule allows is denied
  instead of waiting on a prompt; subagents inherit the same rules.
- **Denies as a second layer.** Read and Edit are both denied the
  runner's file-command files (`$RUNNER_TEMP/_runner_file_commands`,
  where a planted `BASH_ENV` or `PATH` entry would run in every later
  step), any `_actions` directory (the installed actions' post scripts),
  `/tmp` (the review action's own post-step comment buffer), dotfiles in
  the home directory, `/proc` (every process's env there holds the
  credentials) and any `.git` under the workspace (the token in
  `remote.origin.url`, and the config the post-job git reads). Home is
  denied as dotfiles only: the workspace and the context directory are
  both under it, and a deny outranks every allow.
- **A credential scan before posting.** The review is public, so the
  payload step replaces any payload whose body, inline comment bodies or
  paths contain the literal value of `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, the job token, or the
  OIDC request and runtime tokens with the notice, and logs an `::error::` naming the variable, never the value.
  An encoded or split copy is not caught; the denies above are what keep
  the session from reading the values in the first place.

Git does run in the workspace after the session: `actions/checkout`'s
post-job cleanup calls `git config --local` and `git submodule foreach`
there, with the job token, the AWS credentials and the OIDC request
variables in its env. The session holds no write grant on the workspace,
and an `always()` step right after the session also deletes the
workspace's `.git`, so the cleanup finds no `.git/config` and returns
early whatever the CLI's rule matching does. PR text written by a third
party reaches the agent only as diff content.

What proves the file scope is `.github/tests/probe-tool-scope.sh`, run by
hand, not CI; see "Tests" below. The contract suite pins the exact rule
lists, which proves what the workflow asks for, not what the CLI
enforces.

A base ref that cannot be resolved, and a head with no diff against a
base that did resolve, each post a notice naming which of the two
happened, rather than an empty-diff review that would read as clean. That
route is taken from the context step's outputs, never from a file in the
directory the agent can write. The agent writes a review payload to a
file; a later shell step validates its shape and posts it with `event`
and `commit_id` set by the workflow, so the bot cannot approve a PR even
if the prompt is subverted, and a crashed agent yields a visible notice
rather than silence. Every notice ends with a hidden
`<!-- ai-review:notice -->` marker, which the payload step strips from
the agent's own text until none is left, nested copies included, and the
next run never takes the head of a review whose body ends with it as the
last reviewed one, so the changes at a notice's head still count as new.

Two consequences of dropping the untrusted inputs. The review cannot dedup
against human review comments, since those are the untrusted channel and
are no longer fetched, so it may repeat a point a reviewer already made.
And the PR title and body are out of context: the review is bound to the
diff and the branch name.

The vendored critics in `.claude/agents/` run no shell command and no
search of their own: the orchestrator prompt hands each one the prepared
diff to `Read`, so the `git diff <base_sha>...HEAD` their files prescribe
is not needed. The session holds no search tool, since the CLI ships no
Grep or Glob built-in, so the context step writes two files in their
place: `files.txt`, every tracked path at the head, and `symbols.txt`,
every line at the head containing an identifier the diff adds or
removes. Identifiers are taken from the diff's added and removed lines by
a pattern that admits only `[A-Za-z0-9_-]`, keeping snake_case, camelCase
and kebab-case tokens and dropping prose words, and each reaches
`git grep` as a single fixed-string argument. A diff line longer than
4096 bytes, typically minified or generated content, is skipped, which
keeps one oversized line from stalling the step. The index keeps the 200
identifiers the diff touches most, at most 20 lines each and 2000 lines
in all, and its header says whether it is complete or which cap cut it
short; when it cannot be built, a stub says so and the review proceeds.
The prompt sends every search a critic file prescribes (the Grep and
Glob it names, `rg`) to those two files and `Read`, and the shell forms -
the `for`/`grep -c` lockstep loop from `CLAUDE.md`, plus
`simplification-reviewer.md`'s `wc -c` measurement and its
build/lint/test step - to `Read`, or to inspection, since the session
has no shell to run a measurement, a build or the `.github/tests/`
suite. The
simplification critic's step that edits a file to try a replacement
works on a copy under the context directory, the only place the session
can write. A critic file that starts prescribing another tool or shell
form needs that override extended in the same change; without it the
critic has no such tool inside its own subagent, which degrades the
review silently instead of failing the job.

## Tests

```bash
.github/tests/run.sh
```

Needs `bash`, `git`, `jq` and `python3` with PyYAML. Nothing invokes it
automatically: this repo runs no CI beyond the review itself, so run it
before pushing a change to `ai-review.yml`.

The step suites extract the `run:` bodies from the committed workflow and
execute them under the command the shell each step declares expands to.
The workflow sets `defaults.run.shell: bash`, which GitHub expands to
`bash --noprofile --norc -eo pipefail {0}`; the harness derives the same
command from the same file, so a step body sees the options it ships
with, `pipefail` included. `gh` and `sleep` are replaced by stubs, so the
code under test is the code that ships. The
contract and spec suites read the same committed workflow as data. What
the suites pin down:

- `workflow-contract.test.sh` - the guarantees that live in the
  structure: per-job token scope, the exact built-in tool set, an agent
  grant with no shell and nothing that reaches the network, a prompt that
  names only tools the session holds and only context files the context
  step writes, the exact allow and deny rule lists
  (no file tool allowed without a path, writes allowed in the context
  directory only, every second-layer deny present for Read and Edit), the
  `dontAsk` mode, the removal of `.git` right after the session, a
  checkout that persists no credentials, the declared `bash` shell every
  step runs under, the step order, and the trigger surface.
- `resolve-step.test.sh` - the per-trigger gate and the five outputs the
  review job runs on, including the branch name, and the refusal of a
  manual trigger whose PR number is not numeric or whose SHA is neither
  the PR's head nor one of its commits.
- `context-step.test.sh` - the files the agent is allowed to read, the
  filtering that keeps third-party text out of them, the delta staying
  inside the diff under review, a notice never standing in for the last
  review, an identifier index that finds uses outside the diff, treats a
  diff line as data, skips over-long lines, and states its caps, and the degraded inputs that
  must warn rather than fail the job.
- `payload-step.test.sh` - every payload whose keys reach the API as one
  review, every one that reaches it as the notice instead, a notice route
  that only the context step's outputs can select, a notice marker that
  only this step can write, nested copies of it included, a payload
  carrying the literal value of a credential in its env going out as the
  notice (an empty credential never matching), and a directory the agent
  plants at a path the payload or post step writes not keeping the run
  from posting. The
  gate checks each element's keys and that its `body` is a string: a
  non-string `body` sends the run to the notice, while a wrong type in
  `path` or `line` reaches the API, and the post step's fold is what
  keeps that finding.
- `post-step.test.sh` - one review per run, and the two recoveries: a
  rejected payload keeps its findings in the body, a transport failure
  keeps its payload and does not publish twice, and an earlier run's
  review of the same head is not mistaken for this run's.
- `spec_untrusted_input_port.test.sh` - the properties that keep
  untrusted input away from the privileged agent: the comment fetch and
  the review POST are shell steps and not prompt instructions, the tool
  grant keeps `Task` and holds no unrestricted or wildcard shell grant,
  `id-token: write`
  is scoped to the `ai-review` job alone, no credential file is written
  on any trigger, and this README does not deny the surface.

A case that needs `gh` behaviour the stub does not have belongs in the
stub, not in a mock of the step: a test that reimplements the step
proves the test.

### Probing the agent's file scope

```bash
.github/tests/probe-tool-scope.sh
CLAUDE_BIN=/path/to/claude .github/tests/probe-tool-scope.sh
```

The contract suite proves which rules the workflow passes, not what the
CLI does with them. This probe does the second, and it needs a signed-in
`claude` CLI and model access, so `run.sh` never calls it: run it by
hand after any change to the agent step's `claude_args`. It builds a
throwaway layout under the home directory shaped like the runner's, with
stand-ins for the runner's file-command files, an installed action,
`/tmp`, home dotfiles and the workspace `.git`, takes the agent step's
flags from the committed workflow with the runner paths swapped for that
layout, and runs the CLI headless with a prompt that attempts every
out-of-scope read and write, and calls `EnterWorktree` and `Bash`, from
the session and from a Task subagent. The subagent's read of the
workspace `.git/config` is the one operation an allow rule admits and
only a deny rule refuses, so it is what shows that subagents inherit the
deny list; its other out-of-scope operations show that they inherit the
allow list. The canary sits on the first line of every stand-in, the
line a successful read is told to quote. The verdict is taken from the
filesystem and the transcript: every stand-in unchanged, no canary
planted outside the scope in the output, no worktree or branch added,
the in-scope reads, the `review.json` write and the subagent's write in
the context directory done, and the session's tool list, from the
CLI's init message, equal to the set `--tools` names. An operation the
model reports as unavailable is counted separately, and fails the probe
when that tool is in the session's list. `WORKFLOW=<file>` points it at another
revision of the workflow, which is how a known-bad grant is shown to
fail it.

What it does not prove: the action installs its own pinned CLI version on
the runner and drives it through the Agent SDK rather than `-p`, so a
probe against a different version says nothing about the runner's until
`CLAUDE_BIN` points at that version, and `/proc` is only exercised on
Linux.

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

Pin a SHA that belongs to the PR. Both manual triggers fail the run when
the SHA is neither the PR's current head nor one of its commits, and
`workflow_dispatch` also fails on a `pr_number` that is not digits only.
GitHub lists at most 250 commits of a PR, so on a longer one only the
current head and those 250 are accepted.

## Skipping

Apply the `skip-ai-review` label to a PR before pushing. Removing the
label does not re-engage the review on its own; push again or use one of
the re-run methods above.
