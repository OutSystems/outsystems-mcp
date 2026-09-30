#!/usr/bin/env bash
# Contract of the "Run a deployment-impact analysis" recipe in the five
# lockstepped skill docs, against the server's deployment-impact contract:
# the launch returns `analysisKey`, `kind`, `analyzedRevision` and
# `sourceEnvironmentKey`; the status poll does not repeat the last two;
# `report` is a verdict only once `impactKnown` is true; and a
# deployment analysis (not `delete: true`) needs an asset that is already
# deployed somewhere in the tenant. Also pins the Rules sentence that
# routes a never-deployed asset to a publish question, the placement of
# the recipe and the Caveats bullet, and the intended wording drifts of root
# `SKILL.md`.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
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

rules_bullet() { # doc -> the "Confirm before tenant-state mutations" Rules bullet
  grep -F -- '- **Confirm before tenant-state mutations.**' "$REPO_ROOT/$1"
}

section_body() { # doc, heading line -> the lines under it, up to the next heading
  awk -v h="$2" '$0 == h { on = 1; next } on && /^#/ { exit } on' "$REPO_ROOT/$1"
}

line_after_recipe() { # doc -> the first line after the recipe's closing blank line
  awk '/^\*\*Run a deployment-impact analysis:\*\*/ { on = 1 }
       on && /^$/ { getline; print; exit }' "$REPO_ROOT/$1"
}

workflow_before_recipe() { # doc -> the workflow heading right above the recipe
  awk '/^\*\*Run a deployment-impact analysis:\*\*/ { print last; exit }
       /^\*\*[^*]+:\*\*$/ { last = $0 }' "$REPO_ROOT/$1"
}

report_tag='`report`'
deletion_variant='The deletion-impact variant'
run_first='rather than asking permission to run it.'
publish_sentence='For an asset that has never been deployed, ask before publishing it rather than running a deletion-impact analysis in its place (see Caveats).'
first_hash=""
first_caveat_hash=""
first_rules_hash=""
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

  check "numbers the recipe steps 1 to 5" \
    "$(printf '%s\n' "$block" | grep -oE '^[0-9]+\.' | tr -d '\n')" "1.2.3.4.5."
  check_no_match "drops the analysis-id wording the launch response no longer matches" \
    "$block" 'returns an analysis id'
  check_match "does not switch to a deletion analysis past a missing deployment" \
    "$block" 'do not switch to `delete: true`'
  check_match "asks before publishing a never-deployed asset" \
    "$block" 'tell the user and ask before publishing it'
  check_match "maps a delete: true launch to the deletion kind" \
    "$block" '`deletion` for a `delete: true` launch, otherwise `deployment`'
  check_match "stops polling on a terminal processStatus" "$block" '`Finished` or `Failed`'
  check_match "bounds the Unknown processStatus retries" \
    "$block" 'If `processStatus` is `Unknown`, poll at most 3 more times while it stays `Unknown`'
  check_match "restarts the Unknown count on any other status" \
    "$block" 'restarting that count whenever a poll returns any other status'
  check_match "stops and reports not known once the Unknown retries run out" \
    "$block" 'if all 3 of those polls return `Unknown`, stop and report the impact as not known'
  check_match "has a verdict only when impactKnown is true and report is present" \
    "$block" 'Only when `impactKnown` is true and `report` is present'
  check_match "never reads an absent or empty report as no impacts" \
    "$block" 'an absent or empty `report` never means "no impacts"'
  check_match "passes on the error of a Failed analysis" \
    "$block" 'reason in `error` when it is `Failed`'
  check_match "reports the real total of a truncated report" \
    "$block" 'When `report.truncated` is true, tell the user the real `report.total`'
  check_match "shows the kept revision and source environment with the verdict" \
    "$(printf '%s\n' "$block" | grep -E '^5\.')" '`analyzedRevision` and `sourceEnvironmentKey`'
  check "keeps the external-library workflow right above the recipe" \
    "$(workflow_before_recipe "$doc")" '**Reference an external library from an app:**'
  check "ends the recipe with a blank line before ## Feedback" \
    "$(line_after_recipe "$doc")" '## Feedback'

  caveat=$(caveat_bullet "$doc")
  check "sits the already-deployed bullet under ### Caveats" \
    "$(section_body "$doc" '### Caveats' | grep -cF -- "$caveat")" 1
  for type in Workflow ExtensionLibrary LowCodeLibrary WidgetLibrary MobileLibrary ExternalLibrary; do
    check_match "names $type as never analysable for deployment" "$caveat" "$type"
  done
  check_match "keeps the precondition off the deletion path" \
    "$caveat" 'A deletion analysis \(`delete: true`\) needs no deployed revision'
  check_match "says a development publish is enough" \
    "$caveat" 'a publish to the development environment is enough'

  check_match "carries the already-deployed Caveats bullet" "$caveat" 'needs an already-deployed asset'
  check_match "states the already-deployed precondition for a deployment analysis" \
    "$caveat" 'never been deployed[^.]*until it is published'

  check_no_match "leaves the report.status enum to the live tool descriptions" \
    "$block" 'NoIssuesFound|WarningsFound|ErrorsFound'
  check_no_match "leaves the impactedAssets cap number to the live tool descriptions" \
    "$block" '(^|[^0-9])200([^0-9]|$)'

  rules=$(rules_bullet "$doc")
  after_run_first=${rules#*"$run_first"}
  before_deletion=${rules%%"$deletion_variant"*}
  check "routes a never-deployed asset to a publish question, right after the run-first sentence" \
    "${after_run_first:0:$((${#publish_sentence} + 1))}" " $publish_sentence"
  check "places the publish sentence right before the deletion-impact clause" \
    "${before_deletion: -$((${#publish_sentence} + 1))}" "$publish_sentence "
  check "keeps the run-first clause once" \
    "$(printf '%s' "$rules" | grep -oF 'run it *before* you ask for confirmation' | wc -l | tr -d ' ')" 1
  check_match "keeps the destructive-action list" "$rules" \
    'starting or rolling back a deployment, publishing OML, uploading/publishing/deleting an external library, and creating an app\.'
  check_match "keeps the deletion-impact confirm-first rule" \
    "$rules" 'name the asset you are about to analyse and get confirmation first'
  check_match "keeps the mentor-session exemption" \
    "$rules" 'Editing in a mentor session changes only the in-memory mentor OML'
  check_match "keeps the destructiveHint backstop" \
    "$rules" "The MCP host's own \`destructiveHint\` prompt is a backstop, not a substitute"

  check "names no literal deployment-impact tool" "$(grep -c deploy_impact "$REPO_ROOT/$doc")" 0
  check_match "keeps the Tools at a glance Deployments bullet" \
    "$(section_body "$doc" '## Tools at a glance')" \
    '^- \*\*Deployments\*\* .+ promote builds across environments, roll back, run impact analyses\.$'

  if [ "$doc" = SKILL.md ]; then
    check_match "keeps root's lazy sign-in drift" "$(cat "$REPO_ROOT/$doc")" 'lazy sign-in'
    check_match "keeps root's setup-fault drift" "$(cat "$REPO_ROOT/$doc")" 'a setup fault, not a retry target'
  else
    check_match "keeps the lazy authentication step wording" "$(cat "$REPO_ROOT/$doc")" 'lazy authentication step'
    check_match "keeps the routed-back-to-setup wording" "$(cat "$REPO_ROOT/$doc")" \
      'routed back to setup, not retried; see First use / setup above'
  fi

  hash=$(printf '%s' "$block" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "recipe is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"

  caveat_hash=$(printf '%s' "$caveat" | git hash-object --stdin)
  [ -n "$first_caveat_hash" ] || first_caveat_hash=$caveat_hash
  check "Caveats bullet is byte-identical to ${DOCS[0]}" "$caveat_hash" "$first_caveat_hash"

  rules_hash=$(printf '%s' "$rules" | git hash-object --stdin)
  [ -n "$first_rules_hash" ] || first_rules_hash=$rules_hash
  check "Rules bullet is byte-identical to ${DOCS[0]}" "$rules_hash" "$first_rules_hash"
done

finish
