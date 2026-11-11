#!/usr/bin/env bash
# Contract of the Caveats bullet that states what a `context_graph`
# match proves (an import or a reference, not a use) and routes "which
# apps import or reference entity X" to `context_search`. No doc may
# claim that `context_search` finds the apps that use an entity, because
# a match proves only an import or a reference. The `context_graph` tool
# description teaches the other rules of `root`, so the bullet carries
# only the match meaning, the route and the no-match answer. A call where no part of `root` matches succeeds with
# a `root_note`, so no doc may name the old `graph_root_not_found` error.
# The bullet is byte-identical in the five lockstepped skill docs.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

caveat_bullet() { # doc -> the context_graph match bullet
  grep -F -- '- **A `context_graph` match proves only that the app imports or references the element, not that it uses it.** To find the apps that import or reference an entity, call `context_search` first' "$REPO_ROOT/$1"
}

first_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  caveat=$(caveat_bullet "$doc")
  check "carries the context_graph match bullet once" "$(printf '%s\n' "$caveat" | grep -c .)" 1

  hash=$(printf '%s' "$caveat" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "bullet is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"

  check_no_match "names no graph_root_not_found" \
    "$(cat "$REPO_ROOT/$doc")" 'graph_root_not_found'
  check_no_match "says no apps that use an entity" \
    "$(cat "$REPO_ROOT/$doc")" 'apps that use an entity'
done

finish
