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

output() { sed -n "s/^$1=//p" "$RT/step-output.txt"; }

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
check "nothing suppresses the review, so the agent step is not skipped" \
  "$(cat "$RT/step-output.txt")" ""
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
# The delta drives which conditional critics the panel spawns, so it is
# only ever a filter over the diff under review, never wider than it.
check "the delta stays inside the diff under review" \
  "$([ "$(wc -l < "$CTX/delta.diff")" -le "$(wc -l < "$CTX/pr.diff")" ] && echo yes)" yes

section "a reviewed head that is not a commit of this pull request"

# A review posted against a commit on the base branch: what a manual
# trigger pinned to a base-branch SHA leaves behind. Diffing from it
# reports every base-branch commit the PR never touched, and the result
# can be larger than the diff under review.
git -C "$REPO_DIR" checkout -q -b mainline "$BASE"
MAIN_TIP=$(commit_file "$REPO_DIR" mainline.txt "mainline")
git -C "$REPO_DIR" update-ref refs/remotes/origin/mainline "$MAIN_TIP"
git -C "$REPO_DIR" checkout -q main
MAIN_REVIEW=$(reviews_file main-tip '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$MAIN_TIP"'"}]]')
context base-branch-review BASE_REF=mainline GH_REVIEWS_FILE="$MAIN_REVIEW"
check "step succeeds" "$STEP_RC" 0
check "the previous head is still reported for the fix scorecard" \
  "$(cat "$CTX/prev-sha.txt")" "$MAIN_TIP"
check_match "the run says why it carries no delta" \
  "$STEP_OUT" "::notice::previously reviewed head ${MAIN_TIP} is not a commit of this pull request"
check "every line counts as changed" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0
check_no_match "so no base-branch history reaches the delta" \
  "$(cat "$CTX/delta.diff")" 'mainline.txt'

# The same rule over a superseded head, the shape a rebase or an amend
# leaves behind: it is reachable here, but it is no longer one of the
# commits this PR contributes.
git -C "$REPO_DIR" checkout -q -b stale "$BASE"
STALE=$(commit_file "$REPO_DIR" stale.txt "stale")
git -C "$REPO_DIR" checkout -q main
STALE_REVIEW=$(reviews_file stale '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$STALE"'"}]]')
context rebased GH_REVIEWS_FILE="$STALE_REVIEW"
check "step succeeds" "$STEP_RC" 0
check_match "the superseded head is reported the same way" \
  "$STEP_OUT" "::notice::previously reviewed head ${STALE} is not a commit of this pull request"
check "and the run re-reviews in full" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0

# The merge-base itself: diffing from it is the whole PR, not a delta.
BASE_REVIEW=$(reviews_file base '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$BASE"'"}]]')
context base-review GH_REVIEWS_FILE="$BASE_REVIEW"
check "step succeeds" "$STEP_RC" 0
check "the merge-base is out of range too" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0

# The base branch reaching the PR through a merge rather than a rebase.
# The merge-base moves to the base tip, so a head reviewed before the
# merge is still an ancestor of HEAD_SHA, while diffing from it reports
# the base-branch commits the merge brought along.
git -C "$REPO_DIR" checkout -q -b merged "$FIRST"
git -C "$REPO_DIR" checkout -q -b advanced "$BASE"
ADVANCED=$(commit_file "$REPO_DIR" advanced.txt "advanced")
git -C "$REPO_DIR" update-ref refs/remotes/origin/advanced "$ADVANCED"
git -C "$REPO_DIR" checkout -q merged
git -C "$REPO_DIR" merge -q --no-edit "$ADVANCED"
MERGED_HEAD=$(commit_file "$REPO_DIR" three.txt "three")
git -C "$REPO_DIR" checkout -q main
MERGED_REVIEW=$(reviews_file merged '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'"}]]')
context merged-base BASE_REF=advanced HEAD_SHA="$MERGED_HEAD" GH_REVIEWS_FILE="$MERGED_REVIEW"
check "step succeeds" "$STEP_RC" 0
check "the base is the merged-in base tip" "$(cat "$CTX/base-sha.txt")" "$ADVANCED"
check_match "a head predating the merge is reported the same way" \
  "$STEP_OUT" "::notice::previously reviewed head ${FIRST} is not a commit of this pull request"
check "and the run re-reviews in full" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0
check_no_match "so no merged-in base history reaches the delta" \
  "$(cat "$CTX/delta.diff")" 'advanced.txt'
check "the delta stays inside the diff under review" \
  "$([ "$(wc -l < "$CTX/delta.diff")" -le "$(wc -l < "$CTX/pr.diff")" ] && echo yes)" yes

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

section "a notice is not a review, so it never becomes the previous head"

# A run that posted "did not complete" reviewed nothing at that head, so
# diffing the next run from it would hide every change that head made.
NOTICE_BODY='The AI review did not complete: the review job produced no usable review payload.\n\n<!-- ai-review:notice -->'
NOTICE_ONLY=$(reviews_file notice-only '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'","body":"'"$NOTICE_BODY"'"}]]')
context notice-only GH_REVIEWS_FILE="$NOTICE_ONLY"
check "step succeeds" "$STEP_RC" 0
check "a head that only carries a notice is not a previous head" "$(cat "$CTX/prev-sha.txt")" ""
check "so there is no delta to narrow the review" "$(wc -c < "$CTX/delta.diff" | tr -d ' ')" 0
check "the notice stays in the prior reviews the agent reads" \
  "$(jq length "$CTX/prior-reviews.json")" 1

REVIEW_THEN_NOTICE=$(reviews_file review-then-notice '[[
  {"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'","body":"## Review"},
  {"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-02T00:00:00Z","commit_id":"'"$HEAD_SHA"'","body":"'"$NOTICE_BODY"'"}
]]')
context review-then-notice GH_REVIEWS_FILE="$REVIEW_THEN_NOTICE"
check "step succeeds" "$STEP_RC" 0
check "the previous head is the last real review, not the newer notice" \
  "$(cat "$CTX/prev-sha.txt")" "$FIRST"
check_match "so the delta keeps what the notice's head changed" \
  "$(cat "$CTX/delta.diff")" '\+\+\+ b/two.txt'

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
  "$(output no_review_notice)" 'the review context could not be prepared'
check_match "and warns against reading it as a clean review" \
  "$(output no_review_notice)" 'Do not read the absence of findings here as a clean review'
check "the agent step is skipped" "$(output skip_review)" 1
check_file_absent "the notice text is not left where the agent could write" "$CTX/no-review.txt"

context no-changes HEAD_SHA="$BASE"
check "a head with no changes does not fail the step" "$STEP_RC" 0
check_match "it is a notice, not a warning" "$STEP_OUT" '::notice::the diff against'
check_match "the notice says there was nothing to review" \
  "$(output no_review_notice)" 'no changes against'
check_no_match "and does not blame the context" \
  "$(output no_review_notice)" 'could not be prepared'
check "the agent step is skipped" "$(output skip_review)" 1

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
