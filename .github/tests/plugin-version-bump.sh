#!/usr/bin/env bash
# Fails when the version in `claude/.claude-plugin/plugin.json` at <head>
# is not higher than at <base>, by SemVer 2.0 precedence. The release
# workflow runs it with the previous release tag as <base> and the new tag
# as <head>. Without a higher version, `claude plugin update` reports
# "already at the latest version" and users never get the release. No
# pull request has to raise the version: the release pull request does
# (CONTRIBUTING.md "Versioning and Releases"). Which files changed between
# the two revisions does not matter to the check.
#
# Usage: plugin-version-bump.sh <base> <head>
# Exits 0 when the check passes, 1 when it fails, 2 on a usage or git error.

set -uo pipefail
export LC_ALL=C

SOURCE=claude/.claude-plugin/plugin.json

[ $# -eq 2 ] || { echo "usage: $0 <base> <head>" >&2; exit 2; }
base=$1 head=$2

for rev in "$base" "$head"; do
  git rev-parse --verify --quiet "$rev^{commit}" >/dev/null || {
    echo "$0: unknown revision: $rev" >&2
    exit 2
  }
done

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
  echo "The plugin version went from $from at $base to $to at $head."
  exit 0
fi

echo "::error file=$SOURCE::The plugin version did not go up from $base to $head (base: ${from:-none}, head: ${to:-none})."
echo "Bump every file in CONTRIBUTING.md \"Versioning and Releases\" to a higher version."
exit 1
