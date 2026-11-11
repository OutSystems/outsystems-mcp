#!/usr/bin/env bash
# Runs `plugin-version-bump.sh` on throwaway repositories. Each case makes
# one commit on top of a base commit and checks the exit status: 0 when
# the check passes, 1 when it fails.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

command -v jq >/dev/null || { echo "missing prerequisite: jq" >&2; exit 1; }

CHECK="$TESTS_DIR/plugin-version-bump.sh"
SOURCE=claude/.claude-plugin/plugin.json

# A new repository whose one commit has the version and a file in each
# plugin folder. Prints its path.
new_repo() { # version
  local r
  r=$(mktemp -d "$WORK/repo.XXXXXX")
  git -C "$r" init -q
  mkdir -p "$r/claude/.claude-plugin" "$r/cursor" "$r/kiro/outsystems" "$r/kiro/agents" "$r/copilot"
  jq -n --arg v "$1" '{name: "outsystems", version: $v}' > "$r/$SOURCE"
  for f in claude/skill.md cursor/skill.md kiro/outsystems/skill.md kiro/agents/a.json copilot/skill.md README.md; do
    echo base > "$r/$f"
  done
  git -C "$r" add -A
  git -C "$r" commit -q -m base
  echo "$r"
}

set_version() { # repo, version
  jq --arg v "$2" '.version = $v' "$1/$SOURCE" > "$1/$SOURCE.tmp" && mv "$1/$SOURCE.tmp" "$1/$SOURCE"
}

# The exit status of the check on a commit on top of a base with the
# version, where the commit sets the version and changes the files.
status() { # base version, head version, changed files...
  local r f
  r=$(new_repo "$1")
  set_version "$r" "$2"
  for f in "${@:3}"; do
    mkdir -p "$r/$(dirname "$f")"
    echo change >> "$r/$f"
  done
  git -C "$r" add -A
  git -C "$r" commit -q --allow-empty -m head
  (cd "$r" && bash "$CHECK" HEAD^1 HEAD >/dev/null 2>&1)
  echo $?
}

section "no shipped plugin content changed"
check "no change at all passes" "$(status 1.0.0 1.0.0)" 0
check "README.md alone passes" "$(status 1.0.0 1.0.0 README.md)" 0
check "copilot/ alone passes" "$(status 1.0.0 1.0.0 copilot/skill.md)" 0
check "kiro/agents/ alone passes" "$(status 1.0.0 1.0.0 kiro/agents/a.json)" 0

section "shipped plugin content changed without a higher version"
for f in claude/skill.md cursor/skill.md kiro/outsystems/skill.md claude/new/file.md; do
  check "$f with the same version fails" "$(status 1.0.0 1.0.0 "$f")" 1
done
check "a lower version fails" "$(status 1.2.0 1.1.9 claude/skill.md)" 1
check "a pre-release of the same core fails" "$(status 1.2.0 1.2.0-rc.1 claude/skill.md)" 1
check "build metadata alone fails" "$(status 1.2.0 1.2.0+b.2 claude/skill.md)" 1
check "a lower pre-release fails" "$(status 1.2.0-rc.2 1.2.0-rc.1 claude/skill.md)" 1
check "a numeric pre-release identifier below an alphanumeric one fails" \
  "$(status 1.2.0-rc 1.2.0-1 claude/skill.md)" 1
check "a shorter pre-release with the same start fails" \
  "$(status 1.2.0-rc.1 1.2.0-rc claude/skill.md)" 1
check "a head version that is not SemVer fails" "$(status 1.0.0 v1.1.0 claude/skill.md)" 1
check "an empty head version fails" "$(status 1.0.0 "" claude/skill.md)" 1

section "shipped plugin content changed with a higher version"
check "a bump with no other change passes" "$(status 1.0.0 1.1.0)" 0
check "a MINOR bump passes" "$(status 1.11.0 1.12.0 claude/skill.md)" 0
check "a PATCH bump passes" "$(status 1.11.0 1.11.1 cursor/skill.md)" 0
check "a MAJOR bump passes" "$(status 1.11.0 2.0.0 kiro/outsystems/skill.md)" 0
check "numbers compare as numbers, not as text" "$(status 1.9.0 1.10.0 claude/skill.md)" 0
check "a release above its pre-release passes" "$(status 1.2.0-rc.1 1.2.0 claude/skill.md)" 0
check "a higher numeric pre-release identifier passes" \
  "$(status 1.2.0-rc.9 1.2.0-rc.10 claude/skill.md)" 0
check "a longer pre-release with the same start passes" \
  "$(status 1.2.0-rc 1.2.0-rc.1 claude/skill.md)" 0

section "usage"
r=$(new_repo 1.0.0)
(cd "$r" && bash "$CHECK" HEAD >/dev/null 2>&1)
check "one argument exits 2" "$?" 2
(cd "$r" && bash "$CHECK" HEAD no-such-rev >/dev/null 2>&1)
check "an unknown revision exits 2" "$?" 2

finish
