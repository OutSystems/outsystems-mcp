# AI PR Review (shared panel)

Every push to a PR triggers an AI code review through the shared panel at
[`OutSystems/rd-ai-review-panel`](https://github.com/OutSystems/rd-ai-review-panel).
This repo owns two files, and nothing else about the review:

- `ai-review.yml` - the caller stub. Pins the panel by exact SHA during
  phase 3 (selftest gate). Flip to `@v1` once that gate promotes.
- `ai-review-config.json` - the per-repo knobs.

## What this repo runs

Narrow, because this repo is not a service. Its content is text an LLM
agent reads (skills, commands, plugin manifests) plus per-harness assets.

Always:

- `architecture-reviewer` - duplication, wrong abstraction, misplaced logic.
- `consistency-reviewer` **+ agent-facing pack** - MD-to-schema drift plus
  tool-name / description / injected-instruction coherence. The primary
  value for this repo, because its whole product IS text a model reads.
- `error-handling-reviewer` - swallowed errors in skill helpers.

Conditional:

- `docs-reviewer` - MD-to-code drift when a skill's example diverges from
  its recipe.
- `simplification-reviewer` **+ context-cost pack** - complexity cost of
  helpers, plus response-payload cost when a helper adds a field to
  something a model reads. The context axis is the point.

Disabled (explicitly, in `Panel.Disabled`), because they would produce
false positives on doc-shaped content or do not apply:

- `security-reviewer` - no secrets/injection/authz surface here.
- `test-reviewer` - no tests in the repo.
- `robustness-reviewer` - no deploy artifact, no ring, no live contract.
- `compliance-reviewer` - no PRC or threat-model artifacts here.

## Required repo configuration

Set once, at the repo level:

| Kind | Name | Value / example |
|---|---|---|
| secret | `AI_REVIEW_AWS_ROLE_ARN` | `arn:aws:iam::<acct>:role/gha-ai-review-bedrock` |
| variable | `AI_REVIEW_AWS_REGION` | `us-east-1` |
| variable | `AI_REVIEW_BEDROCK_MODEL` | `us.anthropic.claude-sonnet-4-6` |

The IAM role's trust policy must include a subject condition allowing
`repo:OutSystems/outsystems-mcp:*`. Same role that ase-toolkit and the
panel repo use; just widen the sub.

## Skipping

Apply the `skip-ai-review` label to a PR. See the panel repo's README
for the full behavior contract.
