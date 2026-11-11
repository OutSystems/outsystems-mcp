#!/usr/bin/env bash
# Fails when the changes from <base> to <head> touch shipped plugin content
# and the version in `claude/.claude-plugin/plugin.json` is not higher at
# <head> than at <base>, by SemVer 2.0 precedence. Without a higher version,
# `claude plugin update` reports "already at the latest version" and users
# never get the change.
#
# Shipped plugin content is every path under `claude/`, `cursor/` and
# `kiro/outsystems/`, the folders the three versioned plugins install
# from. The Copilot recipes, the root SKILL.md and `kiro/agents/` reach
# users as copied files, not through a plugin update, so a change to them
# needs no bump.
#
# Usage: plugin-version-bump.sh <base> <head>
# Exits 0 when the check passes, 1 when it fails, 2 on a usage or git error.

set -uo pipefail
export LC_ALL=C

SOURCE=claude/.claude-plugin/plugin.json
CONTENT=(claude cursor kiro/outsystems)

[ $# -eq 2 ] || { echo "usage: $0 <base> <head>" >&2; exit 2; }
base=$1 head=$2

changed=$(git diff --name-only "$base" "$head" -- "${CONTENT[@]}") || exit 2
if [ -z "$changed" ]; then
  echo "No change under ${CONTENT[*]}: no version bump needed."
  exit 0
fi

version_at() { # rev
  git show "$1:$SOURCE" 2>/dev/null | jq -r '.version // empty | strings' 2>/dev/null
}
from=$(version_at "$base")
to=$(version_at "$head")

# Exit status 0 when $b has a higher precedence than $a. A value that is
# not SemVer 2.0 compares as not higher, so the check fails closed.
# Build metadata has no effect on precedence.
higher() { # a, b
  jq -n -e --arg a "$1" --arg b "$2" '
    def parse:
      capture("^(?<core>(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*))(-(?<pre>[0-9A-Za-z.-]+))?(\\+[0-9A-Za-z.-]+)?$")
      | { core: (.core | split(".") | map(tonumber)),
          pre: (if .pre then .pre | split(".") else [] end) };
    def ident: if test("^(0|[1-9][0-9]*)$") then [0, tonumber] else [1, .] end;
    # -1, 0 or 1. A release ranks above any pre-release of the same core.
    def cmp_pre($x; $y):
      if $x == $y then 0
      elif $x == [] then 1
      elif $y == [] then -1
      else
        ([range([$x, $y] | map(length) | min)]
          | map(($x[.] | ident) as $p | ($y[.] | ident) as $q
                | if $p < $q then -1 elif $p > $q then 1 else 0 end)
          | map(select(. != 0)) | first)
        // (if ($x | length) < ($y | length) then -1 else 1 end)
      end;
    ($a | parse) as $x | ($b | parse) as $y
    | $y.core > $x.core or ($y.core == $x.core and cmp_pre($x.pre; $y.pre) < 0)
  ' >/dev/null 2>&1
}

if higher "$from" "$to"; then
  echo "Plugin content changed and the version went from $from to $to."
  exit 0
fi

echo "::error file=$SOURCE::Plugin content changed, but the version did not go up (base: ${from:-none}, head: ${to:-none})."
echo "Bump every file in CONTRIBUTING.md \"Versioning and Releases\" to a higher version."
echo "Changed plugin files:"
printf '  %s\n' $changed
exit 1
