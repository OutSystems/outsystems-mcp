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
  check_match "$1: carries the marker the next run's delta skips" "$(final .body)" \
    '<!-- ai-review:notice -->$'
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

# The gate checks that `path` and `line` are there, not what they hold. A
# wrong type in either reaches the API instead, where the post step's
# fold keeps the finding the notice would have thrown away.
payload comment-wrong-types '{"body":"s","comments":[{"path":5,"line":null,"body":"MUST: the finding"}]}'
check "an element with the right keys and wrong types is passed through" \
  "$(final '.comments|length')" 1
check_match "and counted as accepted" "$STEP_OUT" 'payload accepted: 1 inline comment'

section "only a notice this step builds carries the notice marker"

# The next run skips any review whose body ends with the marker, so agent
# text that carried it would drop a real review's head from the delta.
payload marker-in-agent-text '{"body":"## Review\n\n<!-- ai-review:notice -->","comments":[{"path":"a.yml","line":3,"body":"x <!-- ai-review:notice -->"}]}'
check "step succeeds" "$STEP_RC" 0
check "the marker is stripped from the summary body" "$(final .body)" '## Review'
check "and from every inline body" "$(final '.comments[0].body')" 'x '
check "the finding keeps its anchor" "$(final '.comments[0]|"\(.path):\(.line)"')" a.yml:3

payload marker-only-body '{"body":"<!-- ai-review:notice -->","comments":[]}'
check_notice "a body that is only the marker"

# One pass over the nested form removes the inner marker and leaves the
# outer one whole.
payload nested-marker '{"body":"## Review\n\n<!-- ai-review:<!-- ai-review:notice -->notice -->","comments":[{"path":"a.yml","line":3,"body":"x <!-- ai-review:<!-- ai-review:notice -->notice -->"}]}'
check "step succeeds" "$STEP_RC" 0
check_no_match "a marker nested inside another is stripped too" "$(final .body)" \
  '<!-- ai-review:notice -->\s*$'
check "leaving the review text" "$(final .body)" '## Review'
check "and the same holds in an inline body" "$(final '.comments[0].body')" 'x '

payload nested-marker-only '{"body":"<!-- ai-review:<!-- ai-review:notice -->notice -->","comments":[]}'
check_notice "a body that is only a nested marker"

section "a payload that carries a credential is not posted"

SECRET_KEY='example-secret-access-key-xxxxxxxx'
# The credentials the step's env holds on the runner: the AWS values the
# credential step exports, and the token passed in for the scan.
CREDS=(AWS_ACCESS_KEY_ID=example-access-key-id-xxxx "AWS_SECRET_ACCESS_KEY=$SECRET_KEY"
  AWS_SESSION_TOKEN=example-session-token-xxxx GH_TOKEN=example-job-token-xxxx)
scanned() { # case name, review.json content, [VAR=VAL overrides ...]
  new_case "$1"
  printf '%s' "$2" > "$CTX/review.json"
  shift 2
  run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR" "${CREDS[@]}" "$@"
}

scanned secret-in-body '{"body":"env dump: '"$SECRET_KEY"'","comments":[]}'
check_notice "the AWS secret key in the body"
check_match "the error names the variable" "$STEP_OUT" \
  '::error::the review payload contains the value of AWS_SECRET_ACCESS_KEY;'
check_no_match "and never prints the value" "$STEP_OUT" "$SECRET_KEY"
check_no_match "the notice does not carry it either" "$(final .body)" "$SECRET_KEY"

scanned secret-in-comment '{"body":"## Review","comments":[{"path":"a.yml","line":3,"body":"see '"$SECRET_KEY"'"}]}'
check_notice "the AWS secret key in an inline comment"
check_match "the error names the variable" "$STEP_OUT" 'contains the value of AWS_SECRET_ACCESS_KEY;'

scanned token-in-path '{"body":"## Review","comments":[{"path":"example-job-token-xxxx","line":3,"body":"x"}]}'
check_notice "the job token in an inline comment's path"
check_match "the error names the variable" "$STEP_OUT" 'contains the value of GH_TOKEN;'

# jq decodes the escape, and what the API would publish is the decoded text.
scanned escaped-secret '{"body":"\u0065xample-access-key-id-xxxx and \u0065xample-session-token-xxxx","comments":[]}'
check_notice "credentials written as JSON escapes"
check_match "every leaked variable is named" "$STEP_OUT" \
  'contains the value of AWS_ACCESS_KEY_ID, AWS_SESSION_TOKEN;'

# An empty value is a substring of every text, so it must not count.
scanned empty-credential '{"body":"## Review\n\nNo findings.","comments":[{"path":"a.yml","line":3,"body":"x"}]}' \
  AWS_SESSION_TOKEN= GH_TOKEN=
check "an empty credential does not trip the scan" "$STEP_RC" 0
check "the review is posted as written" "$(final .body)" '## Review

No findings.'
check "with its findings" "$(final '.comments|length')" 1
check_no_match "and nothing is reported" "$STEP_OUT" '::error::'

scanned clean-review '{"body":"## Review\n\nMUST: an example- prefix alone is not a credential.","comments":[{"path":"a.yml","line":3,"body":"finding"}]}'
check "a review that carries none of them passes" "$STEP_RC" 0
check_match "and is accepted" "$STEP_OUT" 'payload accepted: 1 inline comment'
check "unchanged" "$(final '.comments[0].body')" finding

section "when the context step already decided there is nothing to review"

new_case notice-wins
printf '%s' '{"body":"I reviewed nothing and found nothing.","comments":[]}' > "$CTX/review.json"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR" \
  SKIP_REVIEW=1 NO_REVIEW_NOTICE='The AI review did not run: this pull request has no changes against abc.'
check "step succeeds" "$STEP_RC" 0
check_match "the context step's notice is what gets posted" "$(final .body)" \
  '^The AI review did not run: this pull request has no changes against abc\.'
check "an agent payload written anyway is discarded" "$(final 'has("comments")')" false
check "still a COMMENT on the pinned head" "$(final '.event + " " + .commit_id')" \
  "COMMENT $HEAD_SHA"
check_match "and the substitution is logged" "$STEP_OUT" \
  '::warning::the context step found nothing to review'
check_match "the notice carries the marker the next run's delta skips" "$(final .body)" \
  '<!-- ai-review:notice -->$'

section "only the context step can route a run to its notice"

# The context directory is inside the agent's write scope, so a file
# there proves nothing about who wrote it.
new_case agent-written-notice
printf '%s' '{"body":"real findings","comments":[{"path":"a","line":1,"body":"x"}]}' > "$CTX/review.json"
printf 'arbitrary text the agent chose' > "$CTX/no-review.txt"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
check "step succeeds" "$STEP_RC" 0
check "the agent's payload still goes through the shape gate" "$(final .body)" "real findings"
check "with its findings" "$(final '.comments|length')" 1
check_no_match "a notice file the agent wrote is ignored" "$(final .body)" 'arbitrary text'

section "a path the agent planted cannot keep the run from posting"

# The context directory is in the agent's write scope. A directory at a
# path this step or the post step writes would make that write fail.
planted() { # case name
  new_case "$1"
  for p in review-final.json review-final.tmp review-folded.json post-response.txt; do
    mkdir -p "$CTX/$p/inner"
  done
}

planted planted-review
printf '%s' '{"body":"## Review","comments":[]}' > "$CTX/review.json"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
check "step succeeds" "$STEP_RC" 0
check_file_exists "review-final.json is a file again" "$CTX/review-final.json"
check "holding the agent's review" "$(final .body)" '## Review'
for p in review-final.tmp review-folded.json post-response.txt; do
  check_file_absent "a directory planted at $p is removed" "$CTX/$p"
done

planted planted-notice
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR" \
  SKIP_REVIEW=1 NO_REVIEW_NOTICE='The AI review did not run: nothing to review.'
check "the skip notice is still written" "$STEP_RC" 0
check_match "as the payload" "$(final .body)" '^The AI review did not run'

new_case planted-then-posted
mkdir -p "$CTX/review-final.json/inner" "$CTX/post-response.txt/inner"
printf '%s' '{"body":"## Review","comments":[]}' > "$CTX/review.json"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
run_step post RUNNER_TEMP="$RT" REPO=o/r PR_NUMBER=7 HEAD_SHA="$HEAD_SHA" \
  GH_TOKEN=token GH_STUB_DIR="$GH_STUB_DIR"
check "the post step then posts the payload" "$STEP_RC" 0
check "exactly once" "$(post_attempts)" 1
check "with the agent's body" "$(jq -r .body "$GH_STUB_DIR/post-1.json")" '## Review'

section "when the context step never ran"

# A failed checkout skips the context step, so the directory it creates
# is not there. This step still runs, and the notice is the run's only
# way to say so.
new_case no-context-dir
rm -rf "$CTX"
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$HEAD_SHA" GH_STUB_DIR="$GH_STUB_DIR"
check_notice "a skipped context step"

section "text the agent writes is data, not shell"

payload quoting '{"body":"`touch '"$WORK"'/pwned` $(touch '"$WORK"'/pwned2) \"quoted\" and $HOME","comments":[]}'
check "step succeeds" "$STEP_RC" 0
check_file_absent "nothing in the body executes" "$WORK/pwned"
check_file_absent "nothing in the body executes, substitution form" "$WORK/pwned2"
check_match "and it reaches the payload unchanged" "$(final .body)" '\$HOME'

finish
