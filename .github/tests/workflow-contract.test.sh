#!/usr/bin/env bash
# Structural contract of ai-review.yml: the properties that hold no
# matter what the step bodies do at runtime, and that a later edit can
# silently undo. Every check here is one externally observable guarantee
# the workflow makes: what each job token may do, what the agent session
# can reach, and the order the steps run in.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# Path lookup over the parsed workflow, printed as compact JSON. `on:` is
# a YAML boolean key, so it is renamed back before the walk.
q() {
  python3 - "$WORKFLOW" "$1" <<'PY'
import json
import sys

import yaml

wf = yaml.safe_load(open(sys.argv[1]))
node = {("on" if k is True else k): v for k, v in wf.items()}
for part in sys.argv[2].split("."):
    if not part:
        continue
    node = node[int(part)] if isinstance(node, list) else node.get(part)
    if node is None:
        break
print(json.dumps(node, sort_keys=True, separators=(",", ":")))
PY
}

step_names() { # job
  python3 - "$WORKFLOW" "$1" <<'PY'
import sys

import yaml

wf = yaml.safe_load(open(sys.argv[1]))
for step in wf["jobs"][sys.argv[2]]["steps"]:
    print(step.get("name") or step.get("uses") or "")
PY
}

step_field() { # job, step name or uses, dot-separated field path
  python3 - "$WORKFLOW" "$1" "$2" "$3" <<'PY'
import json
import sys

import yaml

wf = yaml.safe_load(open(sys.argv[1]))
for step in wf["jobs"][sys.argv[2]]["steps"]:
    if (step.get("name") or step.get("uses")) == sys.argv[3]:
        node = step
        for part in sys.argv[4].split("."):
            if part:
                node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                break
        print(json.dumps(node, sort_keys=True, separators=(",", ":")))
        break
else:
    sys.exit(f"step not found: {sys.argv[3]}")
PY
}

index_of() { # job, step name
  step_names "$1" | grep -nxF -- "$2" | cut -d: -f1
}

CHECKOUT="actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"
AGENT="Critic-loop review"

section "token scope: no permission is granted wider than the job that uses it"

check "workflow-level permissions are read-only on contents" \
  "$(q permissions)" '{"contents":"read"}'
check "resolve holds pull-requests: read and no OIDC" \
  "$(q jobs.resolve.permissions)" '{"contents":"read","pull-requests":"read"}'
check "ai-review is the only job with id-token: write and pull-requests: write" \
  "$(q jobs.ai-review.permissions)" \
  '{"contents":"read","id-token":"write","pull-requests":"write"}'
check "the issues: scope is granted nowhere" \
  "$(grep -cE '^ *issues:' "$WORKFLOW")" 0

section "agent session: no token in its env, no tool that can spend one"

check "the agent step's env carries only the Bedrock switch" \
  "$(step_field ai-review "$AGENT" env)" '{"CLAUDE_CODE_USE_BEDROCK":"1"}'

claude_args=$(step_field ai-review "$AGENT" with.claude_args)
check_match "allowedTools is quoted, so the action cannot widen a pattern while tokenizing" \
  "$claude_args" '--allowedTools \\"[A-Za-z,]+\\"'
check_no_match "no Bash grant, git included" "$claude_args" 'Bash'
check_no_match "no network-capable tool" "$claude_args" 'WebFetch|WebSearch|mcp__'
# Equality, not presence: dropping Write leaves the agent unable to emit
# review.json, and every run then posts the "did not complete" notice.
check "the grant is exactly the set the prompt and the payload step depend on" \
  "$(printf '%s' "$claude_args" | sed -n 's/.*--allowedTools \\"\([^\\]*\)\\".*/\1/p')" \
  'Read,Grep,Glob,Task,Write,Edit'
check_match "the context directory is added to the file tools' scope" \
  "$claude_args" '--add-dir \$\{\{ runner.temp \}\}/ai-review'

prompt=$(step_field ai-review "$AGENT" with.prompt)
check_no_match "the prompt makes no GitHub API call of its own" "$prompt" 'gh (api|pr) '
# The directory named in the prompt is the one `--add-dir` grants and the
# one the payload step reads back; a drift denies the agent's reads and
# strands review.json where nothing looks for it.
check "the prompt reads the context from the granted directory" \
  "$(printf '%s' "$prompt" | grep -co 'CONTEXT = \${{ runner.temp }}/ai-review')" 1
check "the prompt writes review.json into the same directory" \
  "$(printf '%s' "$prompt" | grep -co '\${{ runner.temp }}/ai-review/review.json')" 1

section "the shell steps take their inputs from the resolved SHA, not the run's"

check "the context step's env pins the resolved PR context" \
  "$(step_field ai-review "Collect the review context" env)" \
  '{"BASE_REF":"${{ needs.resolve.outputs.base_ref }}","GH_TOKEN":"${{ secrets.GITHUB_TOKEN }}","HEAD_REF":"${{ needs.resolve.outputs.head_ref }}","HEAD_SHA":"${{ needs.resolve.outputs.head_sha }}","PR_NUMBER":"${{ needs.resolve.outputs.pr_number }}","REPO":"${{ github.repository }}"}'
check "the payload step stamps the resolved SHA onto the review" \
  "$(step_field ai-review "Build the review payload" env)" \
  '{"HEAD_SHA":"${{ needs.resolve.outputs.head_sha }}"}'
check "the post step probes for a duplicate against the resolved SHA" \
  "$(step_field ai-review "Post the review (exactly one, event=COMMENT)" env)" \
  '{"GH_TOKEN":"${{ secrets.GITHUB_TOKEN }}","HEAD_SHA":"${{ needs.resolve.outputs.head_sha }}","PR_NUMBER":"${{ needs.resolve.outputs.pr_number }}","REPO":"${{ github.repository }}"}'

section "checkout: the pinned SHA, with no token written into .git/config"

check "checkout pins the resolved SHA with full history and no persisted credentials" \
  "$(step_field ai-review "$CHECKOUT" with)" \
  '{"fetch-depth":0,"persist-credentials":false,"ref":"${{ needs.resolve.outputs.head_sha }}"}'

section "step order: the context is prepared before any credential is assumed"

ctx_i=$(index_of ai-review "Collect the review context")
aws_i=$(index_of ai-review "Configure AWS credentials (OIDC -> Bedrock)")
agent_i=$(index_of ai-review "$AGENT")
payload_i=$(index_of ai-review "Build the review payload")
post_i=$(index_of ai-review "Post the review (exactly one, event=COMMENT)")
check "context step runs before the AWS credential step" \
  "$([ "$ctx_i" -lt "$aws_i" ] && echo yes)" yes
check "the agent runs after the context is on disk" \
  "$([ "$agent_i" -gt "$ctx_i" ] && echo yes)" yes
check "the payload is built, then posted, after the agent" \
  "$([ "$payload_i" -gt "$agent_i" ] && [ "$post_i" -gt "$payload_i" ] && echo yes)" yes

section "one review per run, including the runs where the agent does not finish"

check "the payload step survives a crashed agent but not a cancellation" \
  "$(step_field ai-review "Build the review payload" if)" '"${{ !cancelled() }}"'
check "the post step survives a crashed agent but not a cancellation" \
  "$(step_field ai-review "Post the review (exactly one, event=COMMENT)" if)" \
  '"${{ !cancelled() }}"'
check_match "the agent is skipped when the context step found nothing to review" \
  "$(step_field ai-review "$AGENT" if)" "steps.context.outputs.skip_review != '1'"

section "trigger surface and concurrency are untouched by the port"

check "pull_request fires on opened, synchronize and reopened only" \
  "$(q on.pull_request.types)" '["opened","synchronize","reopened"]'
check "issue_comment fires on created only" "$(q on.issue_comment.types)" '["created"]'
check "workflow_dispatch still takes pr_number and sha" \
  "$(q on.workflow_dispatch.inputs | python3 -c 'import json,sys; print(",".join(sorted(json.load(sys.stdin))))')" \
  'pr_number,sha'
check_match "in-progress runs are cancelled for pushes only" \
  "$(q concurrency.cancel-in-progress)" "github.event_name == 'pull_request'"
check "resolve exposes head_ref, the only remaining source of the branch name" \
  "$(q jobs.resolve.outputs.head_ref)" '"${{ steps.resolve.outputs.head_ref }}"'

section "the harness runs what the runner runs"

extract_steps
for slug in resolve context payload post; do
  if step_has_interpolation "$slug"; then
    check "$slug step body is plain shell, parameterised through env" \
      "carries a \${{ }} interpolation" "plain shell"
  else
    check "$slug step body is plain shell, parameterised through env" \
      "plain shell" "plain shell"
  fi
done

for slug in context payload post; do
  check "$slug step body names the granted context directory" \
    "$(grep -c 'CTX="${RUNNER_TEMP}/ai-review"' "$STEPS/$slug.sh")" 1
done

finish
