#!/usr/bin/env bash
# Spec-conformance suite for `ai-review.yml`, derived from the ticket's
# success criteria alone: the untrusted-input-to-privileged-agent path is
# closed by moving the PR-review-comment fetch and the review POST into
# workflow shell steps, the agent keeps no unrestricted shell but keeps
# `Task`, `id-token: write` is scoped to the `ai-review` job, and the
# companion README no longer claims the workflow has no secrets,
# injection or authz surface.
#
# Every assertion reads the committed workflow as data (structure and
# command shape), never a copy of it.

set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

README="$REPO_ROOT/.github/workflows/README.md"
F="$WORK/facts"
mkdir -p "$F"

python3 - "$WORKFLOW" "$F" <<'PY' || { echo "fact extraction failed" >&2; exit 1; }
import json
import os
import re
import sys

import yaml

path, outdir = sys.argv[1], sys.argv[2]
raw = open(path).read()
wf = yaml.safe_load(raw)

# PyYAML (YAML 1.1) parses a bare `on:` key as the boolean True.
on = None
for key in (True, "on", "true"):
    if isinstance(wf, dict) and key in wf:
        on = wf[key]
        break
if isinstance(on, dict):
    events = sorted(str(k) for k in on)
elif isinstance(on, list):
    events = sorted(str(k) for k in on)
elif isinstance(on, str):
    events = [on]
else:
    events = []

jobs = (wf.get("jobs") or {}) if isinstance(wf, dict) else {}


def perm_pairs(obj):
    p = (obj or {}).get("permissions")
    if isinstance(p, dict):
        return [(str(k), str(v)) for k, v in p.items()]
    if isinstance(p, str):
        return [("__shorthand__", p)]
    return []


def logical_lines(text):
    """Join backslash continuations so one shell command is one line."""
    if not text:
        return []
    joined = re.sub(r"\\\s*\n\s*", " ", text)
    return [ln.strip() for ln in joined.splitlines() if ln.strip()]


HEREDOC = re.compile(
    r"^(?P<pre>.*?)<<-?\s*(?P<q>['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)(?P=q)\s*$",
    re.M,
)


def heredocs(text):
    """Yield (opening-line-prefix, body) for every heredoc in a run body."""
    out = []
    if not text:
        return out
    for m in HEREDOC.finditer(text):
        tag = m.group("tag")
        rest = text[m.end():]
        end = re.search(r"^\s*%s\s*$" % re.escape(tag), rest, re.M)
        out.append((m.group("pre"), rest[: end.start()] if end else rest))
    return out


PROMPTISH_KEY = re.compile(r"prompt|instruction", re.I)
AGENT_USES = re.compile(r"claude|anthropic|codex|gemini|copilot", re.I)
ALLOWED_FLAG = re.compile(r"--allowed[-_]?tools[=\s]+", re.I)
ALLOWED_KEY = re.compile(r"^allowed[-_]?tools$", re.I)

prompt_parts, run_parts, allowed_parts = [], [], []
agent_steps, uses_list = [], []
agent_run_bodies = []
env_secrets = []

SECRET_REF = re.compile(r"secrets\.[A-Za-z0-9_]+")


def collect_env_secrets(scope, env):
    if not isinstance(env, dict):
        return
    for k, v in env.items():
        for m in SECRET_REF.finditer(str(v)):
            env_secrets.append("%s\t%s\t%s" % (scope, k, m.group(0)))


def scan_allowed(s):
    for m in ALLOWED_FLAG.finditer(s):
        tail = s[m.end():]
        allowed_parts.append(re.split(r"\s--[A-Za-z]", tail)[0])


collect_env_secrets("workflow", wf.get("env") if isinstance(wf, dict) else None)

for jname, job in jobs.items():
    job = job or {}
    collect_env_secrets("job:%s" % jname, job.get("env"))
    for step in job.get("steps") or []:
        step = step or {}
        uses = str(step.get("uses") or "")
        run = str(step.get("run") or "")
        with_ = step.get("with") if isinstance(step.get("with"), dict) else {}
        senv = step.get("env") if isinstance(step.get("env"), dict) else {}
        name = str(step.get("name") or uses or "<unnamed>")
        if uses:
            uses_list.append("%s\t%s" % (jname, uses))
        if run:
            run_parts.append(run)

        blob = json.dumps(with_) + " " + run + " " + uses
        is_agent = bool(AGENT_USES.search(uses)) or bool(ALLOWED_FLAG.search(blob))
        for k in with_:
            if ALLOWED_KEY.match(str(k)):
                is_agent = True

        for k, v in with_.items():
            if isinstance(v, str):
                scan_allowed(v)
                if ALLOWED_KEY.match(str(k)):
                    allowed_parts.append(v)
        scan_allowed(run)

        if is_agent:
            agent_steps.append("%s\t%s" % (jname, name))
            if run:
                agent_run_bodies.append(run)
            for k, v in with_.items():
                if isinstance(v, str) and PROMPTISH_KEY.search(str(k)):
                    prompt_parts.append(v)
            for k, v in senv.items():
                prompt_parts.append(str(v))
            # An agent invoked from a shell step carries its prompt in a
            # heredoc, not in the surrounding plumbing.
            for _pre, body in heredocs(run):
                prompt_parts.append(body)

        # A prompt assembled by a plain shell step is still agent context.
        for pre, body in heredocs(run):
            if re.search(r"prompt", pre, re.I):
                prompt_parts.append(body)

run_lines, prompt_lines = [], []
for r in run_parts:
    run_lines += logical_lines(r)
for p in prompt_parts:
    prompt_lines += logical_lines(p)
agent_run_lines = []
for r in agent_run_bodies:
    agent_run_lines += logical_lines(r)

API = r"(gh\s+api|curl|api\.github\.com|gh\s+pr\s+view)"
POST_METHOD = r"(--method[=\s]+POST|-X[=\s]*POST)"


def is_review_post(line):
    if re.search(r"gh\s+pr\s+review", line, re.I):
        return True
    return bool(
        re.search(API, line, re.I)
        and re.search(POST_METHOD, line, re.I)
        and re.search(r"reviews", line, re.I)
    )


def is_comment_fetch(line):
    return bool(
        re.search(API, line, re.I)
        and re.search(r"comments", line, re.I)
        and not re.search(POST_METHOD, line, re.I)
    )


review_post_runs = [l for l in run_lines if is_review_post(l)]
review_post_prompt = [l for l in prompt_lines if is_review_post(l)]
review_post_agent = [l for l in agent_run_lines if is_review_post(l)]
comment_fetch_runs = [l for l in run_lines if is_comment_fetch(l)]
comment_fetch_prompt = [l for l in prompt_lines if is_comment_fetch(l)]

# The fetched comments must be the bot's own prior findings, so the
# fetching step has to select by author somewhere in its body.
author_filter = 0
for r in run_parts:
    if any(is_comment_fetch(l) for l in logical_lines(r)):
        if re.search(r"\[bot\]|\.login|user\.login|include_comments_by_actor|actor", r, re.I):
            author_filter += 1

allowed = "\n".join(allowed_parts)


def w(name, text):
    with open(os.path.join(outdir, name), "w") as fh:
        fh.write(text if text.endswith("\n") or text == "" else text + "\n")


w("prompt.txt", "\n".join(prompt_lines))
w("runs.txt", "\n".join(run_lines))
w("allowed.txt", allowed)
w("events.txt", "\n".join(events))
w("jobs.txt", "\n".join(str(j) for j in jobs))
w("uses.txt", "\n".join(uses_list))
w("agent_steps.txt", "\n".join(agent_steps))
w("env_secrets.txt", "\n".join(env_secrets))
w(
    "top_perms.txt",
    "\n".join("%s\t%s" % kv for kv in perm_pairs(wf if isinstance(wf, dict) else {})),
)
w(
    "job_perms.txt",
    "\n".join(
        "%s\t%s\t%s" % (j, k, v)
        for j, job in jobs.items()
        for k, v in perm_pairs(job or {})
    ),
)
w("raw.txt", raw)

counts = {
    "REVIEW_POST_RUNS": len(review_post_runs),
    "REVIEW_POST_PROMPT": len(review_post_prompt),
    "REVIEW_POST_AGENT": len(review_post_agent),
    "COMMENT_FETCH_RUNS": len(comment_fetch_runs),
    "COMMENT_FETCH_PROMPT": len(comment_fetch_prompt),
    "COMMENT_FETCH_AUTHOR_FILTER": author_filter,
    "AGENT_STEPS": len(agent_steps),
    "PROMPT_CHARS": len("\n".join(prompt_lines)),
    "ALLOWED_CHARS": len(allowed),
}
w("counts.env", "\n".join("%s=%d" % kv for kv in sorted(counts.items())))
w(
    "diag.txt",
    "review POST (runs):\n  "
    + "\n  ".join(review_post_runs)
    + "\nreview POST (prompt):\n  "
    + "\n  ".join(review_post_prompt)
    + "\ncomment fetch (runs):\n  "
    + "\n  ".join(comment_fetch_runs)
    + "\ncomment fetch (prompt):\n  "
    + "\n  ".join(comment_fetch_prompt),
)
PY

# shellcheck source=/dev/null
. "$F/counts.env"

ALLOWED=$(cat "$F/allowed.txt")
PROMPT=$(cat "$F/prompt.txt")
TOP_PERMS=$(cat "$F/top_perms.txt")
JOB_PERMS=$(cat "$F/job_perms.txt")
EVENTS=$(cat "$F/events.txt")
JOBS=$(cat "$F/jobs.txt")
USES=$(cat "$F/uses.txt")
ENV_SECRETS=$(cat "$F/env_secrets.txt")
RAW=$(cat "$F/raw.txt")
README_TEXT=$([ -f "$README" ] && cat "$README" || echo "")

# --- criterion 1: the agent's context is only the diff and the bot's own
# prior findings; the comment fetch and the review POST are shell steps.
# (Scanner finding: AI agent configured with dangerous tools.)
section "criterion 1: untrusted input and publishing leave the prompt"

check_match "the workflow declares an AI agent step" "$AGENT_STEPS" '^[1-9]'
check_match "a workflow shell step fetches the PR review comments" \
  "$COMMENT_FETCH_RUNS" '^[1-9]'
check "no prompt-side PR-comment fetch remains" "$COMMENT_FETCH_PROMPT" 0
check_match "the comment-fetching shell step selects by comment author" \
  "$COMMENT_FETCH_AUTHOR_FILTER" '^[1-9]'
check_match "a workflow shell step posts the review" "$REVIEW_POST_RUNS" '^[1-9]'
check "no prompt-side review POST remains" "$REVIEW_POST_PROMPT" 0
check "the posting step is not an agent step" "$REVIEW_POST_AGENT" 0
check_match "the agent receives a prompt at all" "$PROMPT_CHARS" '^[1-9]'
check_no_match "the prompt does not interpolate PR-controlled title or body" \
  "$PROMPT" 'github\.event\.[A-Za-z_.]*(title|body)'
check_no_match "the prompt does not interpolate the PR branch name" \
  "$PROMPT" '(github\.head_ref|head\.ref)'
check_no_match "an action-level comment filter does not substitute for the prompt-side fetch" \
  "$PROMPT" '(gh +api|curl|api\.github\.com).*comments'

# --- criterion 2: tool grant and the panel must-not-break. The other
# must-not-break, one review per run, is a runtime property of the post
# step's two recoveries rather than of the workflow's text; it is
# asserted in post-step.test.sh.
# (Scanner finding: CI workflow with access to secrets. The tool surface
# is the actionable half; "publicly exposed" is not.)
section "criterion 2: tool grant narrowed, panel intact"

check_match "an allowed-tools grant is declared" "$ALLOWED_CHARS" '^[1-9]'
check_no_match "no unrestricted shell grant" "$ALLOWED" '(^|[^A-Za-z_])Bash([^(]|$)'
check_no_match "no wildcard shell grant" "$ALLOWED" 'Bash\((\*|:\*)\)'
check_no_match "no file-mutating tool granted to the agent" \
  "$ALLOWED" '(^|[^A-Za-z])(Write|Edit|MultiEdit|NotebookEdit)([^A-Za-z]|$)'
check_match "Task stays granted so the critic panel can be spawned" "$ALLOWED" '(^|[^A-Za-z])Task([^A-Za-z]|$)'
check_match "the agent still spawns the critic panel" "$RAW" 'Task'

# --- criterion 3: OIDC scoping.
# (Scanner finding: high-privilege workflow. Credential scope is the
# assessed property, so the grant is narrowed to the job that uses it.)
section "criterion 3: id-token: write scoped to the ai-review job"

check_match "a job named ai-review exists" "$JOBS" '^ai-review$'
check_no_match "the workflow-level permissions block grants no id-token" \
  "$TOP_PERMS" 'id-token'
check_match "the ai-review job grants id-token: write" \
  "$JOB_PERMS" '^ai-review'$'\t''id-token'$'\t''write$'
check "exactly one job grants id-token" \
  "$(printf '%s\n' "$JOB_PERMS" | grep -c 'id-token')" 1
check_no_match "the resolve job grants no id-token" \
  "$JOB_PERMS" '^resolve'$'\t''id-token'
check "no secret is exposed at workflow or job env scope" "$ENV_SECRETS" ""

# --- criterion 3 (cont.): credentials are never materialized to a file,
# on any trigger, so nothing the agent step could read outlives the step
# that assumed the role.
section "no credential file is written on any trigger"

check_no_match "no shared credentials file is written" \
  "$RAW" '(\.aws/credentials|AWS_SHARED_CREDENTIALS_FILE|aws configure set|credentials-file|credential_file)'
check_no_match "no unpinned AWS credential action" \
  "$USES" 'configure-aws-credentials@v?[0-9]+(\.[0-9]+)*$'

# --- criterion 4: the companion README no longer denies the surface.
section "criterion 4: the workflows README no longer denies the surface"

check_file_exists "the companion README exists" "$README"
check_no_match "the README no longer claims there is no secrets/injection/authz surface" \
  "$README_TEXT" '[Nn]o (secrets?|injection|authz|authorization)[^.]{0,60}(surface|risk)'

# --- out of scope: the pull_request path and the 14 recorded runs stay.
section "out of scope: the pull_request trigger is untouched"

check_match "the pull_request trigger is still served" "$EVENTS" '^pull_request$'
check_no_match "no ref pin was added that would strand the recorded runs" \
  "$RAW" 'ref:refs/heads/main'

finish
