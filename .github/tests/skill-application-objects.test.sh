#!/usr/bin/env bash
# Contract of the Rules bullet that says Application Objects apply to ODC.
# An agent asked about Application Objects on an ODC application denied
# that they exist there, because no skill doc mentioned them. The bullet is
# byte-identical in the five lockstepped skill docs, says that they apply to
# ODC as well as to O11, forbids denying that, says that the server cannot
# report AO consumption yet unless `tools/list` offers a tool for it, and
# points to the Subscription section of the ODC Portal for the overall count
# and consumption.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

ao_bullet() { # doc -> the Application Objects Rules bullet
  grep -F -- '- **Application Objects apply to ODC.**' "$REPO_ROOT/$1"
}

bullet_hash() { # doc -> hash of its bullet, or a marker no other doc shares when it has none
  local bullet
  bullet=$(ao_bullet "$1")
  if [ -n "$bullet" ]; then
    printf '%s' "$bullet" | git hash-object --stdin
  else
    printf 'no bullet in %s\n' "$1"
  fi
}

in_rules() { # doc -> 1 when the bullet sits under the ## Rules heading, else 0
  awk -v bullet='- **Application Objects apply to ODC.**' \
    '/^## /{ rules = ($0 == "## Rules") } rules && index($0, bullet) == 1 { found = 1 } END { print found + 0 }' \
    "$REPO_ROOT/$1"
}

reference_hash=$(bullet_hash "${DOCS[0]}")
for doc in "${DOCS[@]}"; do
  section "$doc"
  bullet=$(ao_bullet "$doc")
  check "carries the Application Objects bullet once" "$(printf '%s\n' "$bullet" | grep -c .)" 1

  check "bullet is byte-identical to ${DOCS[0]}" "$(bullet_hash "$doc")" "$reference_hash"

  check "sits under the Rules heading" "$(in_rules "$doc")" 1
  check_match "says Application Objects apply on ODC as well as on O11" "$bullet" 'on ODC as well as on O11'
  check_match "forbids saying they do not exist on ODC" "$bullet" 'Never tell a user that AOs do not exist on ODC'
  check_match "says the server cannot report AO consumption unless tools/list offers a tool" "$bullet" 'Unless `tools/list` offers a tool that reports AO consumption, say that this server cannot report AO consumption yet'
  check_match "points to the Subscription section of the ODC Portal" "$bullet" 'Subscription section of the ODC Portal'
done

finish
