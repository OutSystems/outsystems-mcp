# AI PR Review

Every push to a PR triggers an AI code review. Unlike
`OutSystems/rd-ai-ase-toolkit`, this repo does not call the shared panel
at [`OutSystems/rd-ai-review-panel`](https://github.com/OutSystems/rd-ai-review-panel)
as a reusable workflow: this repo is public and does not share the
internal `GIT_HUB_CLONE_TOKEN` org secret the panel's cross-repo checkout
needs, so `ai-review.yml` runs standalone and the critic panel is
vendored directly into `.claude/agents/`.

- `ai-review.yml` - the full workflow: trigger gating, SHA pinning, OIDC
  Bedrock auth, and the inline review prompt.
- `.claude/agents/*.md` - the critic panel, adapted from the shared
  panel's composed output for this repo's shape (skill docs, slash
  commands, plugin manifests - no compiled language, no CI to gate on).

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
`architecture-reviewer`, `compliance-reviewer`. This repo has no
secrets/injection/authz surface, no test suite, no deploy artifact or ring,
no module-boundary complexity worth a dedicated pass, and no PRC or
threat-model artifacts.

Max 3 review rounds; MUST and SHOULD findings post inline, COULD and
lower collapse into the review body.

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
