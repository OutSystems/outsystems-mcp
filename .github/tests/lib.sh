#!/usr/bin/env bash
# Shared harness for the `ai-review.yml` tests.
#
# The `run:` bodies are extracted from the committed workflow and executed
# under the shell Actions gives them (`bash -e -o pipefail`), so a test
# exercises the shipped script instead of a copy that can drift from it.
# `gh` and `sleep` are replaced by stubs on PATH: the stub reproduces the
# two real-CLI behaviours the step bodies depend on (`--slurp` is rejected
# together with `--jq`, and `--include` prints the status line the post
# step greps) and makes the POST status scriptable.

set -uo pipefail

TESTS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$TESTS_DIR/../.." && pwd)
WORKFLOW="${WORKFLOW:-$REPO_ROOT/.github/workflows/ai-review.yml}"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/ai-review-tests.XXXXXX")
STEPS="$WORK/steps"
STUBS="$WORK/bin"
mkdir -p "$STEPS" "$STUBS"
trap 'rm -rf "$WORK"' EXIT

_checks=0
_failures=0

# Git must not read the developer's own identity or hooks.
export HOME="$WORK/home"
export GIT_CONFIG_GLOBAL="$WORK/gitconfig"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
mkdir -p "$HOME"
: > "$GIT_CONFIG_GLOBAL"

# --- assertions -------------------------------------------------------

_report() { # pass?, name, detail
  _checks=$((_checks + 1))
  if [ "$1" = 0 ]; then
    printf 'ok %d - %s\n' "$_checks" "$2"
  else
    _failures=$((_failures + 1))
    printf 'not ok %d - %s\n' "$_checks" "$2"
    printf '%s\n' "$3" | sed 's/^/    /'
  fi
}

check() { # name, actual, expected
  if [ "$2" = "$3" ]; then _report 0 "$1"; else
    _report 1 "$1" "expected: $3
actual:   $2"
  fi
}

check_match() { # name, text, extended regex
  if printf '%s' "$2" | grep -qE -- "$3"; then _report 0 "$1"; else
    _report 1 "$1" "expected a match for: $3
in: $2"
  fi
}

check_no_match() { # name, text, extended regex
  if printf '%s' "$2" | grep -qE -- "$3"; then
    _report 1 "$1" "expected no match for: $3
in: $2"
  else _report 0 "$1"; fi
}

check_file_exists() { # name, path
  if [ -f "$2" ]; then _report 0 "$1"; else _report 1 "$1" "missing file: $2"; fi
}

check_file_absent() { # name, path
  if [ -e "$2" ]; then _report 1 "$1" "unexpected file: $2"; else _report 0 "$1"; fi
}

section() { printf '# %s\n' "$1"; }

finish() {
  printf '# %d checks, %d failed\n' "$_checks" "$_failures"
  [ "$_failures" -eq 0 ] || exit 1
  exit 0
}

# --- step extraction --------------------------------------------------

# Writes the `run:` body of each named step to $STEPS/<slug>.sh.
extract_steps() {
  python3 - "$WORKFLOW" "$STEPS" <<'PY'
import sys
import yaml

workflow, outdir = sys.argv[1], sys.argv[2]
slugs = {
    "Resolve PR context and apply per-trigger gate": "resolve",
    "Collect the review context": "context",
    "Build the review payload": "payload",
    "Post the review (exactly one, event=COMMENT)": "post",
}
found = set()
for job in yaml.safe_load(open(workflow))["jobs"].values():
    for step in job.get("steps", []):
        slug = slugs.get(step.get("name"))
        if slug is None:
            continue
        with open(f"{outdir}/{slug}.sh", "w") as fh:
            fh.write(step["run"])
        found.add(slug)
missing = sorted(set(slugs.values()) - found)
if missing:
    sys.exit("step not found in the workflow: " + ", ".join(missing))
PY
}

# An interpolation left in a body would mean the harness runs something
# the runner never sees, so the suites assert on this before running.
step_has_interpolation() { # slug
  grep -q '\${{' "$STEPS/$1.sh"
}

# --- stubs ------------------------------------------------------------

install_stubs() {
  cat > "$STUBS/gh" <<'STUB'
#!/usr/bin/env bash
# Scriptable `gh api` stub.
#   GH_STUB_DIR       where POST payloads and the attempt count are recorded
#   GH_POST_CODES     comma-separated HTTP status per POST attempt (default 201)
#   GH_FAIL_ENDPOINTS comma-separated endpoint substrings whose reads fail hard
#   GH_REVIEWS_FILE / GH_COMMENTS_FILE / GH_PR_FILE  canned responses
dir="${GH_STUB_DIR:?GH_STUB_DIR is required}"
slurp=0; use_jq=0; include=0; method=""; endpoint=""; input=""; jq_expr=""
prev=""
for arg in "$@"; do
  case "$prev" in
    --method) method="$arg" ;;
    --input) input="$arg" ;;
    --jq|-q) jq_expr="$arg" ;;
  esac
  case "$arg" in
    --slurp) slurp=1 ;;
    --jq|-q) use_jq=1 ;;
    --template|-t) use_jq=1 ;;
    --include|-i) include=1 ;;
    repos/*) endpoint="$arg" ;;
  esac
  prev="$arg"
done

if [ "$slurp" = 1 ] && [ "$use_jq" = 1 ]; then
  echo 'the `--slurp` option is not supported with `--jq` or `--template`' >&2
  exit 1
fi

# Reads only: a POST's outcome is scripted through GH_POST_CODES, which
# is what lets a case fail the duplicate probe while the POST behaves.
if [ -n "${GH_FAIL_ENDPOINTS:-}" ] && [ "$method" != POST ]; then
  IFS=, read -ra _pats <<<"$GH_FAIL_ENDPOINTS"
  for _p in "${_pats[@]}"; do
    case "$endpoint" in
      *"$_p"*) echo "gh: HTTP 500 on $endpoint" >&2; exit 1 ;;
    esac
  done
fi

if [ "$method" = POST ]; then
  n=$(cat "$dir/post-count" 2>/dev/null || echo 0)
  n=$((n + 1))
  printf '%s\n' "$n" > "$dir/post-count"
  [ -z "$input" ] || cp "$input" "$dir/post-$n.json"
  code=$(printf '%s' "${GH_POST_CODES:-201}" | cut -d, -f"$n")
  [ -n "$code" ] || code=201
  if [ "$include" = 1 ]; then printf 'HTTP/2.0 %s\n\n' "$code"; fi
  if [ "$code" -ge 300 ]; then
    printf 'gh: the request failed with HTTP %s\n' "$code" >&2
    exit 1
  fi
  printf '{"id":1,"state":"COMMENTED"}\n'
  exit 0
fi

case "$endpoint" in
  */reviews)  body="${GH_REVIEWS_FILE:-$dir/empty-pages.json}" ;;
  */comments) body="${GH_COMMENTS_FILE:-$dir/empty-pages.json}" ;;
  *)          body="${GH_PR_FILE:-$dir/empty-object.json}" ;;
esac
if [ "$use_jq" = 1 ]; then jq -r "$jq_expr" "$body"; else cat "$body"; fi
STUB

  cat > "$STUBS/sleep" <<'STUB'
#!/usr/bin/env bash
# Keeps the post step's rate-limit pause out of the suite's runtime, and
# records it so a test can assert the pause happened.
printf '%s\n' "$*" >> "${GH_STUB_DIR:?GH_STUB_DIR is required}/sleeps.txt"
STUB

  chmod +x "$STUBS/gh" "$STUBS/sleep"
  printf '[[]]\n' > "$WORK/empty-pages.json"
  printf '{}\n' > "$WORK/empty-object.json"
  export PATH="$STUBS:$PATH"
}

# Fresh per-case state: a context directory and a clean POST ledger.
new_case() { # case name -> sets RT, CTX, GH_STUB_DIR
  RT="$WORK/$1"
  CTX="$RT/ai-review"
  GH_STUB_DIR="$RT/stub"
  rm -rf "$RT"
  mkdir -p "$CTX" "$GH_STUB_DIR"
  cp "$WORK/empty-pages.json" "$WORK/empty-object.json" "$GH_STUB_DIR/"
  export GH_STUB_DIR
}

post_attempts() { cat "$GH_STUB_DIR/post-count" 2>/dev/null || echo 0; }

# Canned paginated response for GH_REVIEWS_FILE / GH_COMMENTS_FILE. The
# stub reads it through `jq`, so the outer array is the page list.
reviews_file() { # name, JSON pages -> echoes the file path
  printf '%s\n' "$2" > "$WORK/reviews-$1.json"
  printf '%s' "$WORK/reviews-$1.json"
}

# --- running a step ---------------------------------------------------

# Runs an extracted body with the runner's shell options. Output (stdout
# and stderr, as the run log interleaves them) lands in STEP_OUT and the
# exit status in STEP_RC.
run_step() { # slug, [VAR=VAL ...]
  local slug="$1"
  shift
  STEP_OUT=$(env "$@" bash --noprofile --norc -eo pipefail "$STEPS/$slug.sh" 2>&1)
  STEP_RC=$?
}

run_step_in() { # dir, slug, [VAR=VAL ...]
  local dir="$1" slug="$2"
  shift 2
  # shellcheck disable=SC2034  # read by the sourcing suite
  STEP_OUT=$(cd "$dir" && env "$@" bash --noprofile --norc -eo pipefail "$STEPS/$slug.sh" 2>&1)
  # shellcheck disable=SC2034  # read by the sourcing suite
  STEP_RC=$?
}

# --- git fixtures -----------------------------------------------------

new_repo() { # dir
  rm -rf "$1"
  mkdir -p "$1"
  git -C "$1" init -q
  git -C "$1" symbolic-ref HEAD refs/heads/main
}

commit_file() { # dir, path, content -> echoes the new sha
  printf '%s\n' "$3" > "$1/$2"
  git -C "$1" add "$2"
  git -C "$1" commit -q -m "touch $2"
  git -C "$1" rev-parse HEAD
}
