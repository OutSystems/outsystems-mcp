#!/usr/bin/env bash
# Structural contract of ai-review.yml: the properties that hold no
# matter what the step bodies do at runtime, and that a later edit can
# silently undo. Every check here is one externally observable guarantee
# the workflow makes: what each job token may do, what the agent session
# can reach, the shell every step runs under, and the order the steps run
# in.

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
# What makes that grant droppable on every trigger, the comment one
# included: nothing here reads an issues endpoint. A comment trigger
# takes its command, its author association and its PR number from the
# event payload, so the only API surface left is the pull. GitHub
# resolves a comment-triggered run against the workflow file on the
# default branch, so this property is provable here and not from a
# pre-merge run of the comment path.
check "every GitHub API path the workflow reaches is a pulls path" \
  "$(grep -oE 'repos/\$\{REPO\}/[a-z]+' "$WORKFLOW" | sort -u | tr '\n' ' ')" \
  'repos/${REPO}/pulls '
# Where the resolve step's fork and skip-label refusals take effect. Drop
# this and a fork PR reaches the one job holding OIDC and the Bedrock
# role, checked out at a fork-controlled SHA.
check "the review job runs only on a resolve that said yes" \
  "$(q jobs.ai-review.if)" "\"needs.resolve.outputs.should_run == 'true'\""

section "agent session: its step env adds only the Bedrock switch, and no tool can spend a token"

check "the agent step's env carries only the Bedrock switch" \
  "$(step_field ai-review "$AGENT" env)" '{"CLAUDE_CODE_USE_BEDROCK":"1"}'

claude_args=$(step_field ai-review "$AGENT" with.claude_args)

# The rule list a flag hands the CLI, one rule per line, tokenized the way
# the action does it: shell words first, then each value split on commas.
tool_rules() { # flag name
  python3 - "$claude_args" "$1" <<'PY2'
import json
import shlex
import sys

words = shlex.split(json.loads(sys.argv[1]))
flag = "--" + sys.argv[2]
for i, word in enumerate(words):
    if word == flag:
        for rule in words[i + 1].split(","):
            print(rule.strip())
PY2
}
allow=$(tool_rules allowedTools)
deny=$(tool_rules disallowedTools)
tools=$(tool_rules tools)
WS='${{ github.workspace }}'
CTXDIR='${{ runner.temp }}/ai-review'

check_match "allowedTools is quoted, so the action cannot widen a pattern while tokenizing" \
  "$claude_args" '--allowedTools \\"[^"]+\\"'
check_match "so is disallowedTools" "$claude_args" '--disallowedTools \\"[^"]+\\"'
check_no_match "no Bash grant, git included" "$claude_args" 'Bash'
# `dontAsk` does not gate every built-in: EnterWorktree runs `git worktree
# add` with no allow rule. Restricting the set is what removes it, and
# every other built-in the review does not use, from the session.
check "the built-in tool set is exactly Task, Read, Edit and Write" "$tools" "Task
Read
Edit
Write"
check "the tool set is passed once" "$(grep -oE -- '--tools( |=)' <<<"$claude_args" | wc -l | tr -d ' ')" 1
check_match "and quoted, like the rule lists" "$claude_args" '--tools \\"[^"]+\\"'
check "every allow rule names a tool in that set" \
  "$(sed 's/(.*//' <<<"$allow" | grep -cvxF -f <(printf '%s\n' "$tools"))" 0
check_no_match "no network-capable tool" "$claude_args" 'WebFetch|WebSearch|mcp__'
# A bare file-tool allow approves that tool on every path on the runner,
# the runner's file commands, /proc and /tmp included.
check "no file tool is allowed without a path" \
  "$(grep -cxE 'Read|Write|Edit|Grep|Glob|MultiEdit|NotebookEdit' <<<"$allow")" 0
# Equality, not presence: a missing Edit grant leaves the agent unable to
# emit review.json, and every run then posts the "did not complete" notice.
check "the grant is exactly the panel, reads of the workspace and the context, and writes to the context" \
  "$allow" "Task
Read(/$WS/**)
Read(/$CTXDIR/**)
Edit(/$CTXDIR/**)"
# `Edit` path rules govern every file-writing tool, Write included; a
# `Write(...)` or `Glob(...)` path rule is accepted by the CLI and never
# consulted, so it would read as a scope that is not there.
check "the only write grant is the context directory" \
  "$(grep -E '^(Edit|Write|MultiEdit|NotebookEdit)' <<<"$allow")" "Edit(/$CTXDIR/**)"
check_no_match "no Write, Grep or Glob path rule stands in for a Read or Edit one" \
  "$claude_args" '(Write|Grep|Glob|MultiEdit|NotebookEdit)\('
check_match "calls no rule allows are denied rather than left waiting on a prompt" \
  "$claude_args" '--permission-mode dontAsk( |$)'
check_match "the context directory is added to the file tools' scope" \
  "$claude_args" '--add-dir \$\{\{ runner.temp \}\}/ai-review'

# Each path is denied to Read and to Edit, because the CLI the action
# installs predates Read denies also covering Write.
check "the deny list is exactly the second layer the step comment names" \
  "$deny" "Read(/$WS/**/.git/**)
Edit(/$WS/**/.git/**)
Read(/\${{ runner.temp }}/_runner_file_commands/**)
Edit(/\${{ runner.temp }}/_runner_file_commands/**)
Read(//**/_actions/**)
Edit(//**/_actions/**)
Read(//tmp/**)
Edit(//tmp/**)
Read(~/.*)
Edit(~/.*)
Read(//proc/**)
Edit(//proc/**)"
# shellcheck disable=SC2088  # a rule's literal text, not a shell path
for path in "/$WS/**/.git/**" '/${{ runner.temp }}/_runner_file_commands/**' \
  '//**/_actions/**' '//tmp/**' '~/.*' '//proc/**'; do
  check "$path is denied to reads and writes alike" \
    "$(grep -cxF -e "Read($path)" -e "Edit($path)" <<<"$deny")" 2
done
# The workspace and the context directory both sit under the runner's
# home, and a deny outranks every allow.
check "no deny covers the whole home directory" \
  "$(grep -cE '^(Read|Edit)\(~/\*' <<<"$deny")" 0

prompt=$(step_field ai-review "$AGENT" with.prompt)
check_no_match "the prompt makes no GitHub API call of its own" "$prompt" 'gh (api|pr) '
# The directory named in the prompt is the one `--add-dir` grants and the
# one the payload step reads back; a drift denies the agent's reads and
# strands review.json where nothing looks for it.
check "the prompt reads the context from the granted directory" \
  "$(printf '%s' "$prompt" | grep -co 'CONTEXT = \${{ runner.temp }}/ai-review')" 1
check "the prompt writes review.json into the same directory" \
  "$(printf '%s' "$prompt" | grep -co '\${{ runner.temp }}/ai-review/review.json')" 1
# Every write the prompt asks for has to land inside the one Edit grant.
check "the prompt sends scratch edits to the context directory, not the workspace" \
  "$(printf '%s' "$prompt" | grep -co 'CONTEXT/scratch/')" 1
check_no_match "and no longer asks for working-tree edits to be undone" "$prompt" 'undo each one with Edit'
# The prompt may only send the session to tools it holds.
check_no_match "the prompt names no tool outside the session's set" "$prompt" \
  '(^|[^A-Za-z])(Grep|Glob|Bash|LS|MultiEdit|NotebookEdit|WebFetch|WebSearch|EnterWorktree|ToolSearch)([^A-Za-z]|$)'
check_match "the prompt names the four tools the session holds" \
  "$prompt" 'only tools are Task, Read, Edit and Write'
# CONTEXT is the Read grant's directory, checked above, so a file the
# prompt names is in scope exactly when the context step writes it
# there; review.json and scratch/ are the agent's own writes.
prompt_files=$(grep -oE 'CONTEXT/[A-Za-z0-9_.-]+' <<<"$prompt" | sed 's#^CONTEXT/##' | sort -u)
extract_steps
for f in $prompt_files; do
  case "$f" in review.json|scratch) continue ;; esac
  check "CONTEXT/$f, named in the prompt, is written by the context step" \
    "$(grep -cF "\"\$CTX/$f\"" "$STEPS/context.sh" | awk '{print ($1 > 0)}')" 1
done
check "the prompt sends the session to the file list and the identifier index" \
  "$(grep -cxE 'files\.txt|symbols\.txt' <<<"$prompt_files")" 2

section "the shell steps take their inputs from the resolved SHA, not the run's"

check "the context step's env pins the resolved PR context" \
  "$(step_field ai-review "Collect the review context" env)" \
  '{"BASE_REF":"${{ needs.resolve.outputs.base_ref }}","GH_TOKEN":"${{ secrets.GITHUB_TOKEN }}","HEAD_REF":"${{ needs.resolve.outputs.head_ref }}","HEAD_SHA":"${{ needs.resolve.outputs.head_sha }}","PR_NUMBER":"${{ needs.resolve.outputs.pr_number }}","REPO":"${{ github.repository }}"}'
# The notice route is read from the context step's outputs, which the
# agent cannot write, never from a file in its write scope. GH_TOKEN is
# there for the credential scan, next to the AWS values the credential
# step exports to every later step.
check "the payload step stamps the resolved SHA, routes on the context step's outputs, and holds the token it scans for" \
  "$(step_field ai-review "Build the review payload" env)" \
  '{"GH_TOKEN":"${{ github.token }}","HEAD_SHA":"${{ needs.resolve.outputs.head_sha }}","NO_REVIEW_NOTICE":"${{ steps.context.outputs.no_review_notice }}","SKIP_REVIEW":"${{ steps.context.outputs.skip_review }}"}'
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

section "the post-job git in the workspace finds no repository config to run"

GIT_STRIP="Remove the workspace git directory"
strip_i=$(index_of ai-review "$GIT_STRIP")
check "the .git removal step runs immediately after the agent" \
  "$([ -n "$strip_i" ] && [ "$strip_i" -eq $((agent_i + 1)) ] && echo yes)" yes
check "and on every outcome of it, a cancelled or failed session included" \
  "$(step_field ai-review "$GIT_STRIP" if)" '"${{ always() }}"'

section "one review per run, including the runs where the agent does not finish"

check "the payload step survives a crashed agent but not a cancellation" \
  "$(step_field ai-review "Build the review payload" if)" '"${{ !cancelled() }}"'
check "the post step survives a crashed agent but not a cancellation" \
  "$(step_field ai-review "Post the review (exactly one, event=COMMENT)" if)" \
  '"${{ !cancelled() }}"'
check_match "the agent is skipped when the context step found nothing to review" \
  "$(step_field ai-review "$AGENT" if)" "steps.context.outputs.skip_review != '1'"
# The guard above resolves through this id. Rename the step's id and
# `steps.context.outputs.skip_review` silently becomes the empty string,
# which passes the `!= '1'` test and runs the panel on every no-diff run.
check "the context step carries the id the agent's guard reads" \
  "$(step_field ai-review "Collect the review context" id)" '"context"'

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
check "the resolve step carries the id those job outputs read" \
  "$(step_field resolve "Resolve PR context and apply per-trigger gate" id)" '"resolve"'

section "the harness runs what the runner runs"

extract_steps

check "the workflow declares bash as every step's default shell" \
  "$(q defaults.run.shell)" '"bash"'
check "no job overrides that default" \
  "$(q jobs.resolve.defaults)$(q jobs.ai-review.defaults)" 'nullnull'
check "no step declares a shell of its own" "$(grep -cE '^ +shell:' "$WORKFLOW")" 1
# GitHub's documented expansion of `shell: bash`. The harness derives the
# command from the workflow, so this pins the derivation as well.
for slug in resolve context strip-git payload post; do
  check "$slug step runs under bash --noprofile --norc -eo pipefail, here and on the runner" \
    "$(cat "$STEPS/$slug.shell")" "bash --noprofile --norc -eo pipefail {0}"
done

# A planted fsmonitor is what the removal defends against, so the case
# plants one and checks that the config holding it is gone.
STRIP_WS="$WORK/strip-git"
new_repo "$STRIP_WS"
commit_file "$STRIP_WS" kept.txt "kept" > /dev/null
git -C "$STRIP_WS" config core.fsmonitor "touch $WORK/fsmonitor-ran"
run_step_in "$STRIP_WS" strip-git GITHUB_WORKSPACE="$STRIP_WS"
check "the removal step succeeds" "$STEP_RC" 0
check_file_absent "and leaves no .git/config for the checkout cleanup to act on" \
  "$STRIP_WS/.git/config"
check_file_exists "while the checked-out files stay" "$STRIP_WS/kept.txt"

for slug in resolve context strip-git payload post; do
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
