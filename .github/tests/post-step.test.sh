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

reviews_file() { # name, JSON pages
  printf '%s\n' "$2" > "$WORK/reviews-$1.json"
  printf '%s' "$WORK/reviews-$1.json"
}

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

ALREADY=$(reviews_file already '[[{"user":{"login":"github-actions[bot]"},"commit_id":"'"$HEAD_SHA"'"}]]')
post transport-failure-already-posted "$WITH_FINDING" GH_POST_CODES=502,201 \
  GH_REVIEWS_FILE="$ALREADY"
check "step succeeds" "$STEP_RC" 0
check "a review the server already created is not duplicated" "$(post_attempts)" 1
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

post transport-failure-twice "$WITH_FINDING" GH_POST_CODES=502,502
check "a second transport failure fails the job" "$([ "$STEP_RC" -ne 0 ] && echo yes)" yes
check "after exactly two attempts" "$(post_attempts)" 2

finish
