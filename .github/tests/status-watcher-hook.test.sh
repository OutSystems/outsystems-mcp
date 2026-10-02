#!/usr/bin/env bash
# Runs the Claude plugin's status-watcher hook the way Claude Code runs it:
# the command string from claude/hooks/hooks.json under `sh -c`, with
# CLAUDE_PLUGIN_ROOT set to the plugin folder and the working directory
# outside it, against sample PreToolUse inputs. A call from the watcher
# passes only as a foreground `sleep <n>` with n >= 1; every other caller
# passes untouched. The hook fails open: Claude Code runs the Bash call when
# a hook exits with anything but 2, so a script the command cannot find
# shows up here as a watcher call that is no longer denied.

set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PLUGIN="$REPO_ROOT/claude"
SCRIPT="$PLUGIN/hooks/limit-watcher-bash.sh"
HOOK_CMD=$(jq -r '.hooks.PreToolUse[] | select(.matcher == "Bash") | .hooks[].command' \
  "$PLUGIN/hooks/hooks.json")
W=outsystems:status-watcher

ALLOWED='0|'
DENIED='2|Denied: status-watcher may run no Bash command except exactly sleep <seconds>, run in the foreground. Poll with your status tools, and use Bash only to wait between polls.'

# Prints "<exit code>|<stderr>" for one hook input.
run_hook() { # input, [plugin root]
  local err rc
  err=$(cd "$WORK" && printf '%s' "$1" |
    CLAUDE_PLUGIN_ROOT="${2:-$PLUGIN}" sh -c "$HOOK_CMD" 2>&1 >/dev/null)
  rc=$?
  printf '%s|%s' "$rc" "$err"
}

# A compact PreToolUse input for one Bash call. An empty agent type is the
# user's own session, whose input carries none.
bash_call() { # agent type, command, run_in_background
  jq -cn --arg agent "$1" --arg cmd "$2" --argjson bg "$3" '
    {session_id: "s1", hook_event_name: "PreToolUse", tool_name: "Bash",
     tool_input: {command: $cmd, description: "d", run_in_background: $bg}}
    + (if $agent == "" then {} else {agent_id: "a1", agent_type: $agent} end)'
}

section "hooks.json runs a plain shell script inside the plugin"
check "the command names the script by \${CLAUDE_PLUGIN_ROOT}" "$HOOK_CMD" \
  'sh "${CLAUDE_PLUGIN_ROOT}/hooks/limit-watcher-bash.sh"'
check_file_exists "the script is in the plugin folder" "$SCRIPT"
check_no_match "the script runs no inline program and no command substitution" \
  "$(grep -v '^[[:space:]]*#' "$SCRIPT")" \
  '(^|[^[:alnum:]_-])(awk|gawk|sed|perl|python3?|node|ruby)([^[:alnum:]_-]|$)|\$\(|`'

section "a status-watcher call passes only as a foreground sleep of at least one second"
check "sleep 30 passes" "$(run_hook "$(bash_call "$W" 'sleep 30' false)")" "$ALLOWED"
check "sleep 1 passes" "$(run_hook "$(bash_call "$W" 'sleep 1' false)")" "$ALLOWED"
check "pretty-printed sleep 30 passes" \
  "$(run_hook "$(bash_call "$W" 'sleep 30' false | jq .)")" "$ALLOWED"
check "input that ends in a newline passes" \
  "$(run_hook "$(bash_call "$W" 'sleep 30' false)"$'\n')" "$ALLOWED"
check "spaces around each colon pass sleep 30" \
  "$(run_hook '{"tool_name" : "Bash", "tool_input" : {"command" : "sleep 30", "run_in_background" : false}, "agent_type" : "outsystems:status-watcher"}')" \
  "$ALLOWED"
check "sleep sent to the background is denied" \
  "$(run_hook "$(bash_call "$W" 'sleep 30' true)")" "$DENIED"
check "sleep 0 is denied" "$(run_hook "$(bash_call "$W" 'sleep 0' false)")" "$DENIED"
check "ls is denied" "$(run_hook "$(bash_call "$W" 'ls' false)")" "$DENIED"
check "sleep followed by another command is denied" \
  "$(run_hook "$(bash_call "$W" 'sleep 30 && ls' false)")" "$DENIED"
check "sleep with a second line is denied" \
  "$(run_hook "$(bash_call "$W" $'sleep 30\nls' false)")" "$DENIED"
check "pretty-printed ls is denied" \
  "$(run_hook "$(bash_call "$W" 'ls' false | jq .)")" "$DENIED"
check "spaces around each colon still deny ls" \
  "$(run_hook '{"tool_name" : "Bash", "tool_input" : {"command" : "ls", "run_in_background" : false}, "agent_type" : "outsystems:status-watcher"}')" \
  "$DENIED"

section "every other caller passes untouched"
check "the user's own session runs ls" "$(run_hook "$(bash_call '' 'ls' false)")" "$ALLOWED"
check "another agent runs ls" \
  "$(run_hook "$(bash_call general-purpose 'ls' false)")" "$ALLOWED"
check "a command that quotes the watcher's agent type is not taken for the watcher" \
  "$(run_hook "$(bash_call '' "echo '\"agent_type\": \"$W\"'" false)")" "$ALLOWED"

section "the script path holds in a plugin folder whose path has a space"
spaced="$WORK/plugin folder/claude"
mkdir -p "$spaced/hooks" && cp "$SCRIPT" "$spaced/hooks/"
check "ls from the watcher is still denied" \
  "$(run_hook "$(bash_call "$W" 'ls' false)" "$spaced")" "$DENIED"

finish
