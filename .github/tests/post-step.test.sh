#!/usr/bin/env bash
# The post step: exactly one review per run. Its two recoveries are not
# interchangeable. A rejected payload (422) has to shed its inline
# anchors but keep every finding's text; a transport failure has to keep
# the payload intact and must not publish a second review for a request
# the server already accepted.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

extract_steps
install_stubs

HEAD_SHA=0123456789abcdef0123456789abcdef01234567
WITH_FINDING='{"event":"COMMENT","commit_id":"'"$HEAD_SHA"'","body":"## Review","comments":[{"path":"a.yml","line":3,"body":"the finding text"}]}'
SUMMARY_ONLY='{"event":"COMMENT","commit_id":"'"$HEAD_SHA"'","body":"## Review","comments":[]}'

post() { # case name, review-final.json content (omitted leaves no file), VAR=VAL...
  local name="$1" body="$2"
  shift 2
  new_case "$name"
  if [ -n "$body" ]; then printf '%s' "$body" > "$CTX/review-final.json"; fi
  run_step post RUNNER_TEMP="$RT" REPO=o/r PR_NUMBER=7 HEAD_SHA="$HEAD_SHA" \
    GH_TOKEN=token GH_STUB_DIR="$GH_STUB_DIR" "$@"
}

sent() { # attempt number, jq filter
  jq -r "$2" "$GH_STUB_DIR/post-$1.json"
}

paused() { [ -f "$GH_STUB_DIR/sleeps.txt" ] && echo yes || echo no; }

section "the accepted payload is posted once, unchanged"

post accepted "$WITH_FINDING"
check "step succeeds" "$STEP_RC" 0
check "exactly one review is posted" "$(post_attempts)" 1
check "with the findings inline" "$(sent 1 '.comments|length')" 1
check "as a COMMENT" "$(sent 1 .event)" COMMENT
check "no rate-limit pause on the happy path" "$(paused)" no

section "no payload at all is a red job, not a silent one"

post no-payload ""
check "the step fails" "$STEP_RC" 1
check_match "with the reason" "$STEP_OUT" '::error::.*review-final.json is missing'
check "and nothing is posted" "$(post_attempts)" 0

section "a rejected payload keeps every finding, in the body"

post rejected "$WITH_FINDING" GH_POST_CODES=422,201
check "step succeeds" "$STEP_RC" 0
check "the review is retried once" "$(post_attempts)" 2
check_match "the retry is announced" "$STEP_OUT" '::warning::posting with inline comments was rejected'
check "the retry drops the anchors the API refused" "$(sent 2 'has("comments")')" false
check_match "it keeps the summary" "$(sent 2 .body)" '## Review'
check_match "under a heading that says why" "$(sent 2 .body)" \
  'Findings that could not be anchored inline'
check_match "with the location of each finding" "$(sent 2 .body)" 'a.yml:3'
check_match "and its text, which the summary never repeated" "$(sent 2 .body)" \
  'the finding text'
check "a validation error is not waited out" "$(paused)" no

post rejected-summary-only "$SUMMARY_ONLY" GH_POST_CODES=422,201
check "a summary-only review is retried as it stands" "$(sent 2 .body)" '## Review'
check_no_match "with no empty heading appended" "$(sent 2 .body)" \
  'could not be anchored inline'

post rejected-twice "$WITH_FINDING" GH_POST_CODES=422,422
check "a rejected retry fails the job" "$([ "$STEP_RC" -ne 0 ] && echo yes)" yes
check "after exactly two attempts" "$(post_attempts)" 2

section "a payload shape the fold cannot walk still posts its summary"

post unfoldable \
  '{"event":"COMMENT","commit_id":"'"$HEAD_SHA"'","body":"## Review","comments":["not an object"]}' \
  GH_POST_CODES=422,201
check "step succeeds" "$STEP_RC" 0
check_match "the fold failure is logged" "$STEP_OUT" \
  '::warning::folding the inline findings into the body failed'
check "the summary is posted on its own" "$(sent 2 .body)" '## Review'
check "with no inline anchors" "$(sent 2 'has("comments")')" false

section "a transport failure keeps the payload and checks before repeating"

post transport-failure "$WITH_FINDING" GH_POST_CODES=502,201
check "step succeeds" "$STEP_RC" 0
check "the review is retried once" "$(post_attempts)" 2
check_match "the retry is announced as a transport failure" "$STEP_OUT" \
  '::warning::posting the review failed with no validation error'
check "the retry carries the same payload, findings included" \
  "$(sent 2 '.comments|length')" 1
check "the secondary rate limit is waited out first" "$(paused)" yes

BOT_AT_HEAD='{"user":{"login":"github-actions[bot]"},"commit_id":"'"$HEAD_SHA"'"}'
ALREADY=$(reviews_file already "[[$BOT_AT_HEAD]]")
post transport-failure-already-posted "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_AFTER_POST_FILE="$ALREADY"
check "step succeeds" "$STEP_RC" 0
check "a review the server already created is not duplicated" "$(post_attempts)" 1
check_match "and that is said out loud" "$STEP_OUT" \
  '::notice::the review was created despite the failed response'

# A re-run on a head an earlier run already reviewed: that review is
# there before this run posts anything, so only a new one proves the
# failed POST landed.
PRIOR_RUN=$(reviews_file prior-run "[[$BOT_AT_HEAD]]")
post transport-failure-same-head-rerun "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_FILE="$PRIOR_RUN"
check "step succeeds" "$STEP_RC" 0
check "an earlier run's review of the same head does not count as this run's" \
  "$(post_attempts)" 2
check_no_match "and the run does not claim its own POST landed" "$STEP_OUT" \
  'the review was created despite the failed response'

PRIOR_AND_LANDED=$(reviews_file prior-and-landed "[[$BOT_AT_HEAD,$BOT_AT_HEAD]]")
post transport-failure-same-head-landed "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_FILE="$PRIOR_RUN" GH_REVIEWS_AFTER_POST_FILE="$PRIOR_AND_LANDED"
check "a POST that landed on top of an earlier run's review is not duplicated" \
  "$(post_attempts)" 1
check_match "and that is said out loud" "$STEP_OUT" \
  '::notice::the review was created despite the failed response'

OLDER_REVIEW=$(reviews_file other-sha '[[{"user":{"login":"github-actions[bot]"},"commit_id":"1111111111111111111111111111111111111111"}]]')
post transport-failure-older-review "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_FILE="$OLDER_REVIEW"
check "a review of an earlier head does not count as this run's" "$(post_attempts)" 2
check "step succeeds" "$STEP_RC" 0

HUMAN=$(reviews_file human '[[{"user":{"login":"a-human"},"commit_id":"'"$HEAD_SHA"'"}]]')
post transport-failure-human-review "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_FILE="$HUMAN"
check "a human review of the same head does not count as this run's" "$(post_attempts)" 2

post transport-failure-probe-down "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_FAIL_ENDPOINTS=reviews
check "a probe that cannot answer fails the job" "$([ "$STEP_RC" -ne 0 ] && echo yes)" yes
check "rather than risk a second review" "$(post_attempts)" 1
check_match "and the run says the outcome is unknown" "$STEP_OUT" \
  '::error::posting the review failed and the check for a review it may still have created could not be made'

# This case runs under the shell the workflow declares for the step. Under
# the runner's undeclared default, `bash -e`, the failed re-count reads as
# an empty count, the comparison errors to false, and the run retries.
check "the post step runs under the declared bash, pipefail included" \
  "$(cat "$STEPS/post.shell")" "bash --noprofile --norc -eo pipefail {0}"
post transport-failure-probe-down-after-post "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_FAIL_AFTER_POST=1
check "a probe that fails after a readable baseline fails the job too" \
  "$([ "$STEP_RC" -ne 0 ] && echo yes)" yes
check "without a second attempt" "$(post_attempts)" 1
check_match "and the run says the outcome is unknown" "$STEP_OUT" \
  '::error::posting the review failed and the check for a review it may still have created could not be made'

post baseline-down-post-ok "$WITH_FINDING" GH_FAIL_ENDPOINTS=reviews
check "an unreadable baseline does not stop a POST that succeeds" "$STEP_RC" 0
check "which is posted once" "$(post_attempts)" 1

post transport-failure-twice "$WITH_FINDING" GH_POST_CODES=502,502
check "a second transport failure fails the job" "$([ "$STEP_RC" -ne 0 ] && echo yes)" yes
check "after exactly two attempts" "$(post_attempts)" 2

finish
