#!/usr/bin/env bash
# The payload step: the gate between what the agent wrote and what the
# repository will see. It decides two things the prompt cannot be trusted
# with: that the review is a COMMENT on the pinned SHA, and that a run
# which produced nothing usable says so instead of going quiet.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

extract_steps
install_stubs

HEAD_SHA=0123456789abcdef0123456789abcdef01234567

payload() { # case name, review.json content (omitted leaves no file)
  new_case "$1"
  if [ "$#" -gt 1 ]; then printf '%s' "$2" > "$CTX/review.json"; fi
  run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
}

final() { jq -r "$1" "$CTX/review-final.json"; }

# Every rejected shape lands on the same notice, so one helper asserts the
# whole contract: the step still succeeds, and the run has exactly one
# thing to post.
check_notice() { # label
  check "$1: step succeeds" "$STEP_RC" 0
  check "$1: posts a COMMENT" "$(final .event)" COMMENT
  check_match "$1: says the review did not complete" "$(final .body)" \
    'The AI review did not complete'
  check "$1: carries no inline comments" "$(final 'has("comments")')" false
}

section "a valid payload keeps its findings and loses its event"

payload valid '{"body":"## Review\n\nOne finding.","comments":[{"path":"a.yml","line":3,"body":"finding"}]}'
check "step succeeds" "$STEP_RC" 0
check "the event is the workflow's, not the agent's" "$(final .event)" COMMENT
check "the commit is the pinned head" "$(final .commit_id)" "$HEAD_SHA"
check "the body survives" "$(final .body)" '## Review

One finding.'
check "the inline findings survive" "$(final '.comments|length')" 1
check "with their anchors" "$(final '.comments[0]|"\(.path):\(.line)"')" a.yml:3
check_match "and the count is logged" "$STEP_OUT" 'payload accepted: 1 inline comment'

section "the agent cannot approve a PR, or review a commit of its choosing"

payload approve '{"event":"APPROVE","commit_id":"deadbeef","body":"looks good","comments":[]}'
check "an APPROVE from the prompt is overridden" "$(final .event)" COMMENT
check "a commit_id from the prompt is overridden" "$(final .commit_id)" "$HEAD_SHA"

payload request-changes '{"event":"REQUEST_CHANGES","body":"no","comments":[]}'
check "so is REQUEST_CHANGES" "$(final .event)" COMMENT

section "a summary-only review is valid"

payload no-comments '{"body":"No findings."}'
check "step succeeds" "$STEP_RC" 0
check "the missing comments key becomes an empty list" "$(final '.comments|length')" 0
check "the body survives" "$(final .body)" "No findings."

section "shapes that parse but the API would reject"

payload missing
check_notice "no payload file"

payload empty ''
check_notice "an empty file"

payload truncated '{"body":"unterminated'
check_notice "a parse error"

payload array '[{"body":"x"}]'
check_notice "a top-level array"

payload string '"just a string"'
check_notice "a bare string"

payload null 'null'
check_notice "a null"

payload empty-body '{"body":"","comments":[]}'
check_notice "an empty body"

payload body-not-string '{"body":{"text":"x"},"comments":[]}'
check_notice "a body that is not a string"

payload comments-string '{"body":"s","comments":"none"}'
check_notice "comments that are not a list"

payload comment-text-only '{"body":"s","comments":["a.yml:3 finding"]}'
check_notice "inline findings as plain strings"

payload comment-other-keys '{"body":"s","comments":[{"file":"a.yml","line":3,"comment":"x"}]}'
check_notice "inline findings under other key names"

payload comment-position '{"body":"s","comments":[{"path":"a.yml","position":4,"body":"x"}]}'
check_notice "an inline finding anchored by position instead of line"

payload comment-body-object '{"body":"s","comments":[{"path":"a.yml","line":3,"body":{"text":"x"}}]}'
check_notice "an inline finding whose body is not a string"

payload one-bad-comment '{"body":"s","comments":[{"path":"a.yml","line":3,"body":"ok"},{"path":"b.yml"}]}'
check_notice "a batch where one finding is malformed"

section "when the context step already decided there is nothing to review"

new_case notice-wins
printf 'The AI review did not run: this pull request has no changes against abc.\n' > "$CTX/no-review.txt"
printf '%s' '{"body":"I reviewed nothing and found nothing.","comments":[]}' > "$CTX/review.json"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
check "step succeeds" "$STEP_RC" 0
check "the context step's notice is what gets posted" "$(final .body)" \
  'The AI review did not run: this pull request has no changes against abc.'
check "an agent payload written anyway is discarded" "$(final 'has("comments")')" false
check "still a COMMENT on the pinned head" "$(final '.event + " " + .commit_id')" \
  "COMMENT $HEAD_SHA"
check_match "and the substitution is logged" "$STEP_OUT" \
  '::warning::the context step found nothing to review'

section "text the agent writes is data, not shell"

payload quoting '{"body":"`touch '"$WORK"'/pwned` $(touch '"$WORK"'/pwned2) \"quoted\" and $HOME","comments":[]}'
check "step succeeds" "$STEP_RC" 0
check_file_absent "nothing in the body executes" "$WORK/pwned"
check_file_absent "nothing in the body executes, substitution form" "$WORK/pwned2"
check_match "and it reaches the payload unchanged" "$(final .body)" '\$HOME'

finish
