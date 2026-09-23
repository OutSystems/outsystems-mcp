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

context_in() { # repo dir, case name, then VAR=VAL overrides
  local dir="$1" name="$2"
  shift 2
  new_case "$name"
  : > "$RT/step-output.txt"
  run_step_in "$dir" context \
    GH_TOKEN=token REPO=o/r PR_NUMBER=7 BASE_REF=main \
    HEAD_SHA="$HEAD_SHA" HEAD_REF=feature/x \
    RUNNER_TEMP="$RT" GITHUB_OUTPUT="$RT/step-output.txt" \
    GH_STUB_DIR="$GH_STUB_DIR" "$@"
}

context() { # case name, then VAR=VAL overrides
  context_in "$REPO_DIR" "$@"
}

output() { sed -n "s/^$1=//p" "$RT/step-output.txt"; }

section "happy path: the files the prompt reads, and nothing else"

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
check "files.txt lists every tracked path at the head" \
  "$(cat "$CTX/files.txt")" "base.txt
one.txt
two.txt"
check_file_exists "symbols.txt is written" "$CTX/symbols.txt"
check_match "and says it is complete when the diff names no identifier" \
  "$(cat "$CTX/symbols.txt")" '# Complete: the diff adds or removes no identifier'
check "the context directory holds exactly the files the prompt names" \
  "$(cd "$CTX" && ls | tr '\n' ' ')" \
  "base-sha.txt delta.diff files.txt head-ref.txt pr.diff prev-sha.txt prior-comments.json prior-reviews.json symbols.txt "
check "nothing suppresses the review, so the agent step is not skipped" \
  "$(cat "$RT/step-output.txt")" ""
check "the index leaves no scratch directory behind in the runner temp" \
  "$(cd "$RT" && ls | tr '\n' ' ')" "ai-review step-output.txt stub "
# Anything left in the checkout is inside the agent's Read scope and
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

# The marker is written by the payload step and matched here, so the
# pair is tested end to end: the notice the payload step builds, posted
# as this bot's review, must never become the previous head.
new_case built-notice
run_step payload RUNNER_TEMP="$RT" HEAD_SHA="$FIRST" GH_STUB_DIR="$GH_STUB_DIR" \
  SKIP_REVIEW=1 NO_REVIEW_NOTICE='The AI review did not run: this pull request has no changes against abc.'
BUILT_NOTICE="$WORK/reviews-built-notice.json"
jq '[[{user:{login:"github-actions[bot]"}, submitted_at:"2026-01-01T00:00:00Z",
       commit_id:.commit_id, body:.body}]]' "$CTX/review-final.json" > "$BUILT_NOTICE"
context built-notice-round-trip GH_REVIEWS_FILE="$BUILT_NOTICE"
check "step succeeds" "$STEP_RC" 0
check "a notice the payload step built is not a previous head" "$(cat "$CTX/prev-sha.txt")" ""

QUOTING=$(reviews_file quoting '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'","body":"## Review\n\nThe payload step appends <!-- ai-review:notice --> to every notice.\n\nOne finding."}]]')
context quoting-review GH_REVIEWS_FILE="$QUOTING"
check "step succeeds" "$STEP_RC" 0
check "a review that quotes the marker mid-body is still the previous head" \
  "$(cat "$CTX/prev-sha.txt")" "$FIRST"

TRAILING=$(reviews_file trailing '[[{"user":{"login":"github-actions[bot]"},"submitted_at":"2026-01-01T00:00:00Z","commit_id":"'"$FIRST"'","body":"'"$NOTICE_BODY"'\r\n"}]]')
context notice-trailing-whitespace GH_REVIEWS_FILE="$TRAILING"
check "a notice whose body gained trailing whitespace is still a notice" \
  "$(cat "$CTX/prev-sha.txt")" ""

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

section "the identifier index: uses of the changed code outside the diff"

IDX_DIR="$WORK/index-repo"
new_repo "$IDX_DIR"
mkdir -p "$IDX_DIR/docs"
printf 'total = compute_total(items)\n' > "$IDX_DIR/caller.sh"
printf 'See compute_total for the sum.\n' > "$IDX_DIR/docs/notes.md"
git -C "$IDX_DIR" add caller.sh docs/notes.md
git -C "$IDX_DIR" commit -q -m base
git -C "$IDX_DIR" update-ref refs/remotes/origin/main main
IDX_HEAD=$(commit_file "$IDX_DIR" lib.sh 'compute_total() { echo "sum of the items"; }')
context_in "$IDX_DIR" index HEAD_SHA="$IDX_HEAD"
check "step succeeds" "$STEP_RC" 0
SYMS=$(cat "$CTX/symbols.txt")
check_match "the identifier the diff adds has a section" "$SYMS" '^## compute_total \(3 matching lines\)'
check_match "the index finds its caller, a file the diff does not touch" "$SYMS" '^caller\.sh:1:total = compute_total\(items\)'
check_match "and a mention in a nested path, by its repository path" "$SYMS" '^docs/notes\.md:1:See compute_total'
check_match "the definition in the diff is indexed too" "$SYMS" '^lib\.sh:1:compute_total\(\)'
check_no_match "entries carry no tree-ish prefix" "$SYMS" "$IDX_HEAD:"
check_no_match "plain prose words are not indexed" "$SYMS" '^## (sum|items|echo|the)( |$)'
check_match "the header names the indexed head" "$SYMS" "^# Where the identifiers this pull request adds or removes appear at $IDX_HEAD"
check_match "and says it is complete" "$SYMS" '# Complete: all 1 identifiers are indexed'
check "files.txt lists the head's tracked paths, nested ones included" \
  "$(cat "$CTX/files.txt")" "caller.sh
docs/notes.md
lib.sh"

section "a diff line is data: its identifiers reach git, never the shell"

META_DIR="$WORK/meta-repo"
new_repo "$META_DIR"
commit_file "$META_DIR" base.txt base > /dev/null
git -C "$META_DIR" update-ref refs/remotes/origin/main main
# shellcheck disable=SC2016  # the command substitutions are the fixture
META_LINE='run_$(touch '"$WORK"'/pwned-index)_x `touch '"$WORK"'/pwned-index2` "$(id)"; my-flag=$GITHUB_OUTPUT && rm_all -rf -e --output=x'
META_HEAD=$(commit_file "$META_DIR" meta.sh "$META_LINE")
context_in "$META_DIR" metachars-index HEAD_SHA="$META_HEAD"
check "step succeeds" "$STEP_RC" 0
check_file_absent "a command substitution in an identifier position runs nothing" "$WORK/pwned-index"
check_file_absent "nor does a backtick form" "$WORK/pwned-index2"
check "nothing reaches the step outputs" "$(cat "$RT/step-output.txt")" ""
check "every section names an identifier made of [A-Za-z0-9_-] alone" \
  "$(grep '^## ' "$CTX/symbols.txt" | grep -cvE '^## [A-Za-z_][A-Za-z0-9_-]* \([0-9]+ matching lines\)$')" 0
check_match "an identifier next to the metacharacters is still indexed" \
  "$(cat "$CTX/symbols.txt")" '^## rm_all \(1 matching lines\)'
check_match "the matching line is quoted verbatim as data" \
  "$(cat "$CTX/symbols.txt")" 'meta\.sh:1:run_\$\(touch '
check_no_match "an option-shaped token is never taken for an identifier" \
  "$(cat "$CTX/symbols.txt")" '^## -'

section "the index is capped, and its header says when it was cut short"

WIDE_DIR="$WORK/wide-repo"
new_repo "$WIDE_DIR"
commit_file "$WIDE_DIR" base.txt base > /dev/null
git -C "$WIDE_DIR" update-ref refs/remotes/origin/main main
WIDE_HEAD=$(commit_file "$WIDE_DIR" many.txt "$(for i in $(seq 1 250); do printf 'ident_%03d\n' "$i"; done)")
context_in "$WIDE_DIR" symbol-cap HEAD_SHA="$WIDE_HEAD"
check "step succeeds" "$STEP_RC" 0
check "no more than 200 identifiers are indexed" "$(grep -c '^## ' "$CTX/symbols.txt")" 200
check_match "the header says the symbol cap truncated it" \
  "$(cat "$CTX/symbols.txt")" '# Truncated: indexed the 200 most frequent of 250 identifiers'

DENSE_DIR="$WORK/dense-repo"
new_repo "$DENSE_DIR"
for i in $(seq 1 120); do for _ in $(seq 1 25); do printf 'dense_%03d\n' "$i"; done; done > "$DENSE_DIR/uses.txt"
git -C "$DENSE_DIR" add uses.txt
git -C "$DENSE_DIR" commit -q -m base
git -C "$DENSE_DIR" update-ref refs/remotes/origin/main main
DENSE_HEAD=$(commit_file "$DENSE_DIR" touch.txt "$(for i in $(seq 1 120); do printf 'dense_%03d\n' "$i"; done)")
context_in "$DENSE_DIR" line-cap HEAD_SHA="$DENSE_HEAD"
check "step succeeds" "$STEP_RC" 0
check_match "an identifier with more matches than the per-identifier cap says how many were left out" \
  "$(cat "$CTX/symbols.txt")" '^\(6 more not shown\)$'
check "the index body, headers and truncation lines included, stays within 2000 lines" \
  "$([ "$(grep -vc '^# ' "$CTX/symbols.txt")" -le 2000 ] && echo yes)" yes
check_match "the header says the line cap truncated it" \
  "$(cat "$CTX/symbols.txt")" '# Truncated: stopped at 2000 lines after [0-9]+ of 120 identifiers'

section "a very long diff line is skipped, and tokenizing stays linear"

LONG_DIR="$WORK/long-repo"
new_repo "$LONG_DIR"
commit_file "$LONG_DIR" base.txt base > /dev/null
git -C "$LONG_DIR" update-ref refs/remotes/origin/main main
{
  echo 'short_line_ident'
  awk 'BEGIN { for (i = 0; i < 400000; i++) printf "long_tok "; print "" }'
  awk 'BEGIN { for (i = 0; i < 300; i++) printf "mid_tok_%d ", i % 50; print "" }'
} > "$LONG_DIR/bundle.txt"
git -C "$LONG_DIR" add bundle.txt
git -C "$LONG_DIR" commit -q -m long
LONG_HEAD=$(git -C "$LONG_DIR" rev-parse HEAD)
started=$SECONDS
context_in "$LONG_DIR" long-line HEAD_SHA="$LONG_HEAD"
elapsed=$((SECONDS - started))
# The bound leaves room for a loaded machine; the quadratic tokenizer this
# guards against needs minutes on this line with BSD awk and hours with gawk.
check "step succeeds" "$STEP_RC" 0
check "a 3.6 MB diff line does not stall the step" "$([ "$elapsed" -le 60 ] && echo yes)" yes
check_match "identifiers on normal lines are indexed" "$(cat "$CTX/symbols.txt")" '^## short_line_ident '
check "identifiers only on the over-long line are not" "$(grep -c '^## long_tok ' "$CTX/symbols.txt")" 0
check_match "a line under the limit with many tokens is tokenized" "$(cat "$CTX/symbols.txt")" '^## mid_tok_1 '

section "an index that cannot be built leaves a stub and does not fail the step"

# A git that fails only the two index commands, so the rest of the step
# still runs against the real repository.
FAILGIT="$WORK/failgit"
mkdir -p "$FAILGIT"
REAL_GIT=$(command -v git)
cat > "$FAILGIT/git" <<STUB
#!/usr/bin/env bash
for arg in "\$@"; do
  case "\$arg" in grep|ls-tree) echo "git: \$arg failed" >&2; exit 128 ;; esac
done
exec "$REAL_GIT" "\$@"
STUB
chmod +x "$FAILGIT/git"
context_in "$IDX_DIR" index-fails HEAD_SHA="$IDX_HEAD" PATH="$FAILGIT:$PATH"
check "step succeeds" "$STEP_RC" 0
check_match "the missing index is logged as a warning" "$STEP_OUT" '::warning::could not build the identifier index'
check_match "and so is the missing file list" "$STEP_OUT" '::warning::could not list the files'
check_match "symbols.txt is a stub that says it could not be built" \
  "$(cat "$CTX/symbols.txt")" '^# The identifier index could not be built for this run'
check "and holds no partial index" "$(grep -c '^## ' "$CTX/symbols.txt")" 0
check_match "files.txt is a stub too" "$(cat "$CTX/files.txt")" '^# The file list could not be built'
check "the review still runs" "$(cat "$RT/step-output.txt")" ""
check_match "the diff is still prepared" "$(cat "$CTX/pr.diff")" '\+\+\+ b/lib.sh'

finish
