#!/bin/sh
# PreToolUse hook for Bash, run by hooks.json. A call from the
# outsystems:status-watcher agent may run only a foreground "sleep <n>", with
# n a whole number of at least 1. Calls from any other agent, and from the
# user's own session, pass untouched.
#
# The hook input arrives on stdin as JSON, compact or pretty-printed, so the
# lines are joined into one and each pattern allows spaces around its colon.
# Keep this file plain shell: the plugin directory's validator follows a plain
# shell script, but blocks a command that runs an inline program it can't read.

input=
while IFS= read -r line || test -n "$line"; do
  input="$input$line"
done

watcher='"agent_type" *: *"outsystems:status-watcher"'
one_sleep='"command" *: *"sleep [1-9][0-9]*"'
background='"run_in_background" *: *true'

if printf '%s' "$input" | grep -Eq "$watcher"; then
  if ! printf '%s' "$input" | grep -Eq "$one_sleep" ||
    printf '%s' "$input" | grep -Eq "$background"; then
    echo 'Denied: status-watcher may run no Bash command except exactly sleep <seconds>, run in the foreground. Poll with your status tools, and use Bash only to wait between polls.' >&2
    exit 2
  fi
fi
exit 0
