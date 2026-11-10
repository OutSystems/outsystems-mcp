#!/usr/bin/env bash
# Contract of the Caveats bullet for `context_graph` with a `root` list.
# The server takes `root` as a comma list and answers the union of what
# the parts match, and it refuses a `root` over 4096 bytes, so the
# bullet tells the agent to split a longer list over more calls. A part
# that selects no element is listed in `unmatched_roots`, and a call
# where no part matches succeeds with a `root_note`, so no doc may name
# the old `graph_root_not_found` error.
# The stored graph holds every library element that the app imports, so
# the bullet says that a match proves a reference, not a use. It routes
# the users and the owner of an entity to `context_search`. It is
# byte-identical in the five lockstepped skill docs.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

caveat_bullet() { # doc -> the root-list Caveats bullet
  grep -F -- '- **`context_graph` reads many elements in one call, and a match proves a reference, not a use.**' "$REPO_ROOT/$1"
}

section_body() { # doc, heading line -> the lines under it, up to the next heading
  awk -v h="$2" '$0 == h { on = 1; next } on && /^#/ { exit } on' "$REPO_ROOT/$1"
}

first_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  caveat=$(caveat_bullet "$doc")
  check "carries the root-list bullet once" "$(printf '%s\n' "$caveat" | grep -c .)" 1
  check "sits the bullet under ### Caveats" \
    "$(section_body "$doc" '### Caveats' | grep -cF -- "$caveat")" 1
  check_match "says root takes a comma list" "$caveat" '`root` takes a comma list'
  check_match "says the answer is the union" "$caveat" 'the answer is the union of what the parts match'
  check_match "asks for one comma list per app" \
    "$caveat" 'send all their keys as one comma list, in one call per app\.'
  check_match "states the root limit and the split" \
    "$caveat" '`root` takes at most 4096 bytes\. Split a longer list over more calls to the same app, and keep every key\.'
  check_match "names unmatched_roots and its bound" \
    "$caveat" 'It lists the first 100 parts, and `unmatched_roots_omitted` counts the rest\.'
  check_match "says a full miss succeeds with a root_note" \
    "$caveat" 'If no part matches, the call succeeds: .*`root_note` says what the miss means'
  check_match "says a match proves a reference, not a use" \
    "$caveat" 'a match proves only that the revision imports or references the element, not that it uses it\.'
  check_match "routes users and owners to context_search" \
    "$caveat" 'or the app that owns an element, call `context_search` first\.'
  check_match "says context_search finds the users of entities only" \
    "$caveat" 'it does not find the users of a library action, block or structure\.'
  check_no_match "names no graph_root_not_found" \
    "$(cat "$REPO_ROOT/$doc")" 'graph_root_not_found'

  hash=$(printf '%s' "$caveat" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "bullet is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"
done

finish
