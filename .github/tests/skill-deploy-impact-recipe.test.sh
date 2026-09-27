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

caveat_bullet() { # doc -> the Caveats bullet the recipe and the Rules bullet point to
  grep -F -- '- **A deployment-impact analysis needs an already-deployed asset.**' "$REPO_ROOT/$1"
}

report_tag='`report`'
first_hash=""
first_caveat_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  block=$(recipe_block "$doc")
  check_match "carries the deployment-impact recipe" "$block" 'Run a deployment-impact analysis'

  check_no_match "does not hardcode the poll kind" "$block" 'kind: "(deployment|deletion)"'
  check_match "polls with the kind the launch returned" "$block" \
    '`kind`[^.]*launch|launch[^.]*`kind`'

  check_match "keeps analyzedRevision from the launch" "$block" '`analyzedRevision`'
  check_match "keeps sourceEnvironmentKey from the launch" "$block" '`sourceEnvironmentKey`'

  check_match "names impactKnown in the recipe" "$block" '`impactKnown`'
  check_match "gates report on impactKnown before reading it" \
    "${block%%"$report_tag"*}" '`impactKnown`'

  caveat=$(caveat_bullet "$doc")
  check_match "carries the already-deployed Caveats bullet" "$caveat" 'needs an already-deployed asset'
  check_match "states the already-deployed precondition for a deployment analysis" \
    "$caveat" 'never been deployed[^.]*until it is published'

  check_no_match "leaves the report.status enum to the live tool descriptions" \
    "$block" 'NoIssuesFound|WarningsFound|ErrorsFound'
  check_no_match "leaves the impactedAssets cap number to the live tool descriptions" \
    "$block" '(^|[^0-9])200([^0-9]|$)'

  hash=$(printf '%s' "$block" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "recipe is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"

  caveat_hash=$(printf '%s' "$caveat" | git hash-object --stdin)
  [ -n "$first_caveat_hash" ] || first_caveat_hash=$caveat_hash
  check "Caveats bullet is byte-identical to ${DOCS[0]}" "$caveat_hash" "$first_caveat_hash"
done

finish
