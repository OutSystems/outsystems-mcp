#!/usr/bin/env bash
# The resolve step: the per-trigger gate, and the five outputs the review
# job runs on. The port added `head_ref`, which is now the only source of
# the branch name, and moved the job's token scope; the gating behaviour
# of all three triggers has to survive both.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

extract_steps
install_stubs

SHA=0123456789abcdef0123456789abcdef01234567
OLDER=89abcdef0123456789abcdef0123456789abcdef
FOREIGN=fedcba9876543210fedcba9876543210fedcba98

resolve() { # case name, then VAR=VAL overrides
  local name="$1"
  shift
  new_case "$name"
  : > "$RT/step-output.txt"
  run_step resolve \
    GH_TOKEN=token EVENT_NAME=pull_request REPO=o/r \
    IS_SAME_REPO_PR=true HAS_SKIP_LABEL=false \
    PR_NUMBER_INPUT= PR_NUMBER_PR=7 PR_NUMBER_COMMENT=7 \
    PR_HEAD_SHA="$SHA" PR_BASE_REF=main PR_HEAD_REF=feature/x \
    SHA_INPUT= COMMENT_BODY= COMMENT_ASSOCIATION= \
    GITHUB_OUTPUT="$RT/step-output.txt" GH_STUB_DIR="$GH_STUB_DIR" \
    "$@"
}

out() { # output key
  grep "^$1=" "$RT/step-output.txt" | head -n1 | cut -d= -f2-
}

pr_json() { # name, response body -> echoes the canned-response path
  printf '%s\n' "$2" > "$WORK/pr-$1.json"
  printf '%s' "$WORK/pr-$1.json"
}

FULL_PR=$(pr_json same-repo '{"base":{"ref":"main"},"head":{"repo":{"full_name":"o/r"},"ref":"feature/x","sha":"'"$SHA"'"}}')
COMMITS=$(pr_json commits '[{"sha":"'"$OLDER"'"},{"sha":"'"$SHA"'"}]')

section "pull_request: resolved from the event payload, with no API call"

# Any API call would fail hard here, so a clean exit is the evidence that
# the pull_request path never reaches for one.
resolve pr-happy GH_FAIL_ENDPOINTS=repos/
check "step succeeds" "$STEP_RC" 0
check "should_run" "$(out should_run)" true
check "pr_number" "$(out pr_number)" 7
check "head_sha is the event's pinned SHA" "$(out head_sha)" "$SHA"
check "base_ref" "$(out base_ref)" main
check "head_ref carries the branch name" "$(out head_ref)" feature/x

section "pull_request: the two documented skips"

resolve pr-fork IS_SAME_REPO_PR=false
check "fork PR does not run" "$(out should_run)" false
check_match "and says why" "$STEP_OUT" '::notice::Fork PR'

resolve pr-skip-label HAS_SKIP_LABEL=true
check "skip-ai-review label does not run" "$(out should_run)" false
check_match "and says why" "$STEP_OUT" '::notice::PR carries skip-ai-review label'

section "workflow_dispatch: SHA comes from the caller, the rest from the API"

resolve dispatch-happy EVENT_NAME=workflow_dispatch SHA_INPUT="$SHA" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$FULL_PR"
check "step succeeds" "$STEP_RC" 0
check "should_run" "$(out should_run)" true
check "head_sha is the caller's SHA, never the API's" "$(out head_sha)" "$SHA"
check "base_ref comes from the API" "$(out base_ref)" main
check "head_ref comes from the API" "$(out head_ref)" feature/x

resolve dispatch-short-sha EVENT_NAME=workflow_dispatch SHA_INPUT=0123456 PR_NUMBER_INPUT=7
check "a non-40-char SHA fails the job" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" '::error::sha input must be a 40-char lowercase hex'

resolve dispatch-uppercase-sha EVENT_NAME=workflow_dispatch PR_NUMBER_INPUT=7 \
  SHA_INPUT=0123456789ABCDEF0123456789ABCDEF01234567
check "an uppercase SHA is rejected too" "$STEP_RC" 1

FORK_PR=$(pr_json fork '{"base":{"ref":"main"},"head":{"repo":{"full_name":"fork/r"},"ref":"feature/x"}}')
resolve dispatch-fork EVENT_NAME=workflow_dispatch SHA_INPUT="$SHA" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$FORK_PR"
check "a manual trigger on a fork head does not run" "$(out should_run)" false
check_match "and names the fork" "$STEP_OUT" 'head is in fork fork/r'

resolve dispatch-api-down EVENT_NAME=workflow_dispatch SHA_INPUT="$SHA" \
  PR_NUMBER_INPUT=7 GH_FAIL_ENDPOINTS=repos/
check "an API failure fails the job instead of reading as a fork" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" '::error::gh api call failed'

NO_REF_PR=$(pr_json no-head-ref '{"base":{"ref":"main"},"head":{"repo":{"full_name":"o/r"},"sha":"'"$SHA"'"}}')
resolve dispatch-no-head-ref EVENT_NAME=workflow_dispatch SHA_INPUT="$SHA" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$NO_REF_PR"
check "a missing head_ref degrades the scope sentence, not the run" "$(out should_run)" true
check "and resolves to empty rather than the string null" "$(out head_ref)" ""

resolve dispatch-non-numeric-pr EVENT_NAME=workflow_dispatch SHA_INPUT="$SHA" \
  PR_NUMBER_INPUT='7/../../other' GH_PR_FILE="$FULL_PR"
check "a pr_number that is not digits fails the job" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" '::error::pr_number input must be a PR number'
check "and resolves nothing" "$(out should_run)" ""

resolve dispatch-multiline-sha EVENT_NAME=workflow_dispatch PR_NUMBER_INPUT=7 \
  SHA_INPUT="$SHA"$'\nshould_run=true' GH_PR_FILE="$FULL_PR"
check "a SHA input with a second line is rejected, not matched line by line" "$STEP_RC" 1
check "so nothing it carries reaches the step outputs" "$(out should_run)" ""

section "manual triggers: the SHA must belong to the PR it is posted to"

resolve dispatch-older-commit EVENT_NAME=workflow_dispatch SHA_INPUT="$OLDER" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$FULL_PR" GH_COMMITS_FILE="$COMMITS"
check "an earlier commit of the PR runs" "$(out should_run)" true
check "on that commit, not the current head" "$(out head_sha)" "$OLDER"

resolve dispatch-foreign-sha EVENT_NAME=workflow_dispatch SHA_INPUT="$FOREIGN" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$FULL_PR" GH_COMMITS_FILE="$COMMITS"
check "a SHA that is not one of the PR's commits fails the job" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" \
  "::error::${FOREIGN} is neither the head nor one of the commits of PR #7"
check "and resolves nothing" "$(out should_run)" ""

resolve dispatch-commits-down EVENT_NAME=workflow_dispatch SHA_INPUT="$OLDER" \
  PR_NUMBER_INPUT=7 GH_PR_FILE="$FULL_PR" GH_FAIL_ENDPOINTS=/commits
check "an unreadable commit list fails the job rather than trusting the SHA" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" '::error::gh api call failed listing the commits of PR #7'

resolve comment-foreign-sha EVENT_NAME=issue_comment COMMENT_ASSOCIATION=MEMBER \
  COMMENT_BODY="/ai-review $FOREIGN" GH_PR_FILE="$FULL_PR" GH_COMMITS_FILE="$COMMITS"
check "the comment trigger refuses a foreign SHA too" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" "::error::${FOREIGN} is neither the head"

section "issue_comment: authorization before SHA validation"

resolve comment-member EVENT_NAME=issue_comment COMMENT_ASSOCIATION=MEMBER \
  COMMENT_BODY="/ai-review $SHA" GH_PR_FILE="$FULL_PR"
check "a member's command runs" "$(out should_run)" true
check "on the SHA they named" "$(out head_sha)" "$SHA"
check "with the branch name from the API" "$(out head_ref)" feature/x

resolve comment-outsider EVENT_NAME=issue_comment COMMENT_ASSOCIATION=NONE \
  COMMENT_BODY="/ai-review $SHA" GH_PR_FILE="$FULL_PR"
check "a non-collaborator's command does not run" "$(out should_run)" false
check_match "and is refused on association" "$STEP_OUT" 'non-collaborator \(author_association=NONE\)'
check_no_match "without telling them what a valid command looks like" \
  "$STEP_OUT" '40-char lowercase hex sha'

resolve comment-no-sha EVENT_NAME=issue_comment COMMENT_ASSOCIATION=OWNER \
  COMMENT_BODY="/ai-review" GH_PR_FILE="$FULL_PR"
check "a bare /ai-review does not run" "$(out should_run)" false
check_match "and an authorized caller does get the usage" "$STEP_OUT" \
  'Usage: /ai-review <40-char lowercase hex sha>'

resolve comment-other-command EVENT_NAME=issue_comment COMMENT_ASSOCIATION=OWNER \
  COMMENT_BODY="/ai-review-please $SHA" GH_PR_FILE="$FULL_PR"
check "a look-alike command does not run" "$(out should_run)" false
check_no_match "and is skipped silently" "$STEP_OUT" '::(warning|error)::'

resolve comment-second-line EVENT_NAME=issue_comment COMMENT_ASSOCIATION=OWNER \
  COMMENT_BODY="please have a look
/ai-review $SHA" GH_PR_FILE="$FULL_PR"
check "the command is read from the first line only" "$(out should_run)" false

# Longer than the pipe's capacity, so a writer piped into `head -n1`
# would take a SIGPIPE, which pipefail turns into a failed step. The
# capacity is 64 KiB on Linux and larger on macOS, and Linux caps one
# environment string at 128 KiB, so the length depends on the platform.
case "$(uname -s)" in
  Darwin) LONG_LEN=200000 ;;
  *)      LONG_LEN=100000 ;;
esac
LONG_TAIL=$(head -c "$LONG_LEN" /dev/zero | tr '\0' x)
resolve comment-long-body EVENT_NAME=issue_comment COMMENT_ASSOCIATION=OWNER \
  COMMENT_BODY="/ai-review $SHA
$LONG_TAIL" GH_PR_FILE="$FULL_PR"
check "a long comment body does not fail the step" "$STEP_RC" 0
check "and its first-line command still runs" "$(out should_run)" true

section "issue_comment: the comment body is data, never shell"

resolve comment-injection EVENT_NAME=issue_comment COMMENT_ASSOCIATION=OWNER \
  COMMENT_BODY='/ai-review $(touch '"$WORK"'/pwned) `touch '"$WORK"'/pwned2` ; touch '"$WORK"'/pwned3' \
  GH_PR_FILE="$FULL_PR"
check "a command substitution in the body does not run" "$(out should_run)" false
check_file_absent "and executes nothing" "$WORK/pwned"
check_file_absent "and executes nothing, backtick form" "$WORK/pwned2"
check_file_absent "and executes nothing, separator form" "$WORK/pwned3"

section "an event the gate does not handle fails loudly"

resolve unknown-event EVENT_NAME=schedule
check "unhandled event fails the job" "$STEP_RC" 1
check_match "with the event named" "$STEP_OUT" '::error::Unhandled event: schedule'

finish
