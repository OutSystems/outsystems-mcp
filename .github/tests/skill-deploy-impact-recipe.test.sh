#!/usr/bin/env bash
# Contract of the "Run a deployment-impact analysis" recipe in the five
# lockstepped skill docs, against the server's deployment-impact contract:
# the launch returns `analysisKey`, `kind`, `analyzedRevision` and
# `sourceEnvironmentKey`; the status poll does not repeat the last two;
# `report` is a verdict only once `impactKnown` is true; and a
# deployment analysis (not `delete: true`) needs an asset that is already
# deployed somewhere in the tenant.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

recipe_block() { # doc -> the recipe, heading through the first blank line
  sed -n '/^\*\*Run a deployment-impact analysis:\*\*/,/^$/p' "$REPO_ROOT/$1"
}

first_line_matching() { # text, extended regex -> 1-based line number or 0
  printf '%s\n' "$1" | grep -nE -- "$2" | head -n 1 | cut -d: -f1 | grep . || echo 0
}

first_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  block=$(recipe_block "$doc")
  check_match "carries the deployment-impact recipe" "$block" 'Run a deployment-impact analysis'

  check_no_match "does not hardcode the poll kind" "$block" 'kind: "(deployment|deletion)"'
  check_match "polls with the kind the launch returned" "$block" \
    '`kind`[^.]*launch|launch[^.]*`kind`'

  check_match "keeps analyzedRevision from the launch" "$block" '`analyzedRevision`'
  check_match "keeps sourceEnvironmentKey from the launch" "$block" '`sourceEnvironmentKey`'

  gate=$(first_line_matching "$block" '`impactKnown`')
  verdict=$(first_line_matching "$block" '`report`')
  check "names impactKnown in the recipe" "$([ "$gate" -gt 0 ] && echo yes || echo no)" yes
  check "gates report on impactKnown before reading it" \
    "$([ "$gate" -gt 0 ] && [ "$verdict" -ge "$gate" ] && echo yes || echo no)" yes

  check_match "states the already-deployed precondition for a deployment analysis" \
    "$(grep -i 'impact' "$REPO_ROOT/$doc")" \
    '(already[- ]deployed|never been deployed|deployed somewhere|has no deployment|publish (it )?first)'

  check_no_match "leaves the report.status enum to the live tool descriptions" \
    "$block" 'NoIssuesFound|WarningsFound|ErrorsFound'
  check_no_match "leaves the impactedAssets cap number to the live tool descriptions" \
    "$block" '(^|[^0-9])200([^0-9]|$)'

  hash=$(printf '%s' "$block" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "recipe is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"
done

finish
