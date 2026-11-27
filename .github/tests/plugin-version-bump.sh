#!/usr/bin/env bash
# Fails when the changes from <base> to <head> touch a plugin's shipped
# content and that plugin's version is not higher at <head> than at
# <base>, by SemVer 2.0 precedence. Without a higher version,
# `claude plugin update` reports "already at the latest version" and users
# never get the change.
#
# Each plugin has its own content and its own version:
# - `outsystems`: every path under `claude/`, `cursor/` and
#   `kiro/outsystems/`, the folders its three versioned copies install
#   from, versioned in `claude/.claude-plugin/plugin.json`. The Copilot
#   recipes, the root SKILL.md and `kiro/agents/` reach users as copied
#   files, not through a plugin update, so a change to them needs no bump.
# - `legacy-modernization`: every path under `legacy-modernization/`,
#   versioned in `legacy-modernization/.claude-plugin/plugin.json`.
# A plugin whose manifest is new at <head> needs only a SemVer version, and
# one whose manifest is gone at <head> needs none.
#
# Usage: plugin-version-bump.sh <base> <head>
# Exits 0 when the check passes, 1 when it fails, 2 on a usage or git error.

set -uo pipefail
export LC_ALL=C

# One line per plugin: its version source, then the folders it ships from.
PLUGINS=(
  "claude/.claude-plugin/plugin.json claude cursor kiro/outsystems"
  "legacy-modernization/.claude-plugin/plugin.json legacy-modernization"
)

[ $# -eq 2 ] || { echo "usage: $0 <base> <head>" >&2; exit 2; }
base=$1 head=$2

has_file() { # rev, path
  git cat-file -e "$1:$2" 2>/dev/null
}

version_at() { # rev, path
  git show "$1:$2" 2>/dev/null | jq -r '.version // empty | strings' 2>/dev/null
}

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

# Exit status 0 when the value is SemVer 2.0: it is higher than the lowest
# version there is, or it is that version.
semver() { # value
  [ "$1" = "0.0.0-0" ] || higher "0.0.0-0" "$1"
}

rc=0
for plugin in "${PLUGINS[@]}"; do
  read -r source folders <<<"$plugin"
  read -r -a content <<<"$folders"
  changed=$(git diff --name-only "$base" "$head" -- "${content[@]}") || exit 2
  if [ -z "$changed" ]; then
    echo "No change under ${content[*]}: no version bump needed."
    continue
  fi
  to=$(version_at "$head" "$source")
  if ! has_file "$head" "$source"; then
    echo "No $source at $head: no plugin version to raise for ${content[*]}."
    continue
  fi
  if ! has_file "$base" "$source"; then
    if semver "$to"; then
      echo "New plugin: $source starts at $to."
      continue
    fi
    echo "::error file=$source::A new plugin needs a SemVer version (head: ${to:-none})."
    rc=1
    continue
  fi
  from=$(version_at "$base" "$source")
  if higher "$from" "$to"; then
    echo "Plugin content under ${content[*]} changed and the version went from $from to $to."
    continue
  fi
  echo "::error file=$source::Plugin content changed, but the version did not go up (base: ${from:-none}, head: ${to:-none})."
  echo "Bump every file CONTRIBUTING.md \"Versioning and Releases\" lists for this plugin to a higher version."
  echo "Changed plugin files:"
  printf '  %s\n' $changed
  rc=1
done
exit "$rc"
