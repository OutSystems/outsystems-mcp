#!/usr/bin/env bash
# The context step: everything the agent session is allowed to know. It
# is also the step that must never fail, because the agent step carries
# no `if:` guard against it and a failed prerequisite would skip straight
# to a review that never happened.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

extract_steps
install_stubs

REPO_DIR="$WORK/repo"
new_repo "$REPO_DIR"
BASE=$(commit_file "$REPO_DIR" base.txt "base")
git -C "$REPO_DIR" update-ref refs/remotes/origin/main main
FIRST=$(commit_file "$REPO_DIR" one.txt "one")
HEAD_SHA=$(commit_file "$REPO_DIR" two.txt "two")

context() { # case name, then VAR=VAL overrides
  local name="$1"
  shift
  new_case "$name"
  : > "$RT/step-output.txt"
  run_step_in "$REPO_DIR" context \
    GH_TOKEN=token REPO=o/r PR_NUMBER=7 BASE_REF=main \
    HEAD_SHA="$HEAD_SHA" HEAD_REF=feature/x \
    RUNNER_TEMP="$RT" GITHUB_OUTPUT="$RT/step-output.txt" \
    GH_STUB_DIR="$GH_STUB_DIR" "$@"
}

section "happy path: the five files the prompt reads, and nothing else"

context happy
check "step succeeds" "$STEP_RC" 0
check "the branch name is passed through verbatim" "$(cat "$CTX/head-ref.txt")" feature/x
check "the base is the merge-base, not the base branch tip" "$(cat "$CTX/base-sha.txt")" "$BASE"
check_match "the diff covers the PR's first commit" "$(cat "$CTX/pr.diff")" '\+\+\+ b/one.txt'
check_match "the diff covers the PR's head commit" "$(cat "$CTX/pr.diff")" '\+\+\+ b/two.txt'
check "a first review has no previous head" "$(cat "$CTX/prev-sha.txt")" ""
check "and no delta" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0
check "prior reviews default to an empty list" "$(cat "$CTX/prior-reviews.json")" "[]"
check "prior inline comments default to an empty list" "$(cat "$CTX/prior-comments.json")" "[]"
check_file_absent "nothing suppresses the review" "$CTX/no-review.txt"
check "so the agent step is not skipped" "$(cat "$RT/step-output.txt")" ""
# Anything left in the checkout is inside the agent's Read/Grep scope and
# would read as a repository change.
check "the step leaves the workspace untouched" \
  "$(git -C "$REPO_DIR" status --porcelain)" ""

section "a branch name is data: it reaches the file, not the shell"

context metachars HEAD_REF='feature/$(touch '"$WORK"'/pwned)`touch '"$WORK"'/pwned2`;x'
check "step succeeds" "$STEP_RC" 0
check "the name is written verbatim" "$(cat "$CTX/head-ref.txt")" \
  'feature/$(touch '"$WORK"'/pwned)`touch '"$WORK"'/pwned2`;x'
check_file_absent "and executes nothing" "$WORK/pwned"
check_file_absent "and executes nothing, backtick form" "$WORK/pwned2"

section "prior findings: this bot's own output only"

MIXED=$(reviews_file mixed '[[
  {"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'"},
  {"user":{"login":"a-human"},"submitted_at":"2026-01-02T00:00:00Z","commit_id":"deadbeef","body":"third-party text"}
]]')
context dedup GH_REVIEWS_FILE="$MIXED" GH_COMMENTS_FILE="$MIXED"
check "reviews by anyone else are dropped at fetch time" \
  "$(jq length "$CTX/prior-reviews.json")" 1
check "so is their text" "$(grep -c 'third-party text' "$CTX/prior-reviews.json")" 0
check "inline comments are filtered the same way" \
  "$(jq length "$CTX/prior-comments.json")" 1
check "the previous head is the newest bot review's commit" \
  "$(cat "$CTX/prev-sha.txt")" "$FIRST"
check_match "the delta covers only what changed since that review" \
  "$(cat "$CTX/delta.diff")" '\+\+\+ b/two.txt'
check_no_match "and not what the previous review already saw" \
  "$(cat "$CTX/delta.diff")" 'b/one.txt'

section "the delta is a two-point diff against the reviewed head"

# The previously reviewed head is on a line that is no longer in the PR,
# the shape a rebase or an amend leaves behind. A three-dot delta would
# start at the merge-base and hide the file that head carried.
git -C "$REPO_DIR" checkout -q -b stale "$BASE"
STALE=$(commit_file "$REPO_DIR" stale.txt "stale")
git -C "$REPO_DIR" checkout -q main
STALE_REVIEW=$(reviews_file stale '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$STALE"'"}]]')
context rebased GH_REVIEWS_FILE="$STALE_REVIEW"
check "step succeeds" "$STEP_RC" 0
check_match "the delta reports the file the reviewed head carried" \
  "$(cat "$CTX/delta.diff")" 'a/stale.txt'

section "a previously reviewed head that is no longer in the clone"

GONE=$(reviews_file gone '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"1111111111111111111111111111111111111111"}]]')
context force-push GH_REVIEWS_FILE="$GONE"
check "a force-pushed previous head does not fail the step" "$STEP_RC" 0
check_match "it is reported" "$STEP_OUT" '::notice::previously reviewed head 1111111111'
check "and every line counts as changed" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0

SAME=$(reviews_file same '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$HEAD_SHA"'"}]]')
context already-reviewed GH_REVIEWS_FILE="$SAME"
check "re-reviewing the same head does not fail the step" "$STEP_RC" 0
check_match "it is reported" "$STEP_OUT" '::notice::the last review already covered'
check "and the full diff is reviewed again" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0

section "a failed fetch degrades the scorecard, it does not fail the run"

context fetch-down GH_FAIL_ENDPOINTS=reviews,comments
check "step succeeds" "$STEP_RC" 0
check_match "the failure is logged for reviews" "$STEP_OUT" '::warning::could not fetch prior reviews'
check_match "the failure is logged for inline comments" \
  "$STEP_OUT" '::warning::could not fetch prior inline comments'
check "prior reviews fall back to an empty list" "$(cat "$CTX/prior-reviews.json")" "[]"
check "prior comments fall back to an empty list" "$(cat "$CTX/prior-comments.json")" "[]"
check "the review still runs" "$(cat "$RT/step-output.txt")" ""

section "the two ways a run has nothing to review are told apart"

context base-gone BASE_REF=deleted-branch
check "an unresolvable base does not fail the step" "$STEP_RC" 0
check_match "it is logged as a warning" "$STEP_OUT" '::warning::the base ref deleted-branch could not be resolved'
check "base-sha.txt holds no ref string a critic could mistake for a SHA" \
  "$(cat "$CTX/base-sha.txt")" ""
check "the diff is empty" "$(wc -c < "$CTX/pr.diff" | tr -d ' ')" 0
check_match "the notice says the context could not be prepared" \
  "$(cat "$CTX/no-review.txt")" 'the review context could not be prepared'
check_match "and warns against reading it as a clean review" \
  "$(cat "$CTX/no-review.txt")" 'Do not read the absence of findings here as a clean review'
check "the agent step is skipped" "$(cat "$RT/step-output.txt")" "skip_review=1"

context no-changes HEAD_SHA="$BASE"
check "a head with no changes does not fail the step" "$STEP_RC" 0
check_match "it is a notice, not a warning" "$STEP_OUT" '::notice::the diff against'
check_match "the notice says there was nothing to review" \
  "$(cat "$CTX/no-review.txt")" 'no changes against'
check_no_match "and does not blame the context" \
  "$(cat "$CTX/no-review.txt")" 'could not be prepared'
check "the agent step is skipped" "$(cat "$RT/step-output.txt")" "skip_review=1"

section "a base ref that exists but shares no history with the head"

git -C "$REPO_DIR" checkout -q --orphan unrelated
git -C "$REPO_DIR" rm -q -rf .
UNRELATED=$(commit_file "$REPO_DIR" other.txt "other")
git -C "$REPO_DIR" update-ref refs/remotes/origin/unrelated "$UNRELATED"
git -C "$REPO_DIR" checkout -q main
context no-merge-base BASE_REF=unrelated
check "step succeeds" "$STEP_RC" 0
check_match "the widened diff is logged" "$STEP_OUT" '::warning::git merge-base origin/unrelated'
check "base-sha.txt still holds a resolved SHA, not origin/<ref>" \
  "$(cat "$CTX/base-sha.txt")" "$UNRELATED"
check "the review runs on the wider diff rather than being skipped" \
  "$(cat "$RT/step-output.txt")" ""

finish
