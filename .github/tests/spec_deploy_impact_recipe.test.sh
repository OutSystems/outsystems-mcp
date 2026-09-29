#!/usr/bin/env bash
# Spec-conformance suite for the deployment-impact recipe, derived from the
# scope statement alone: all five skill docs teach the launch -> poll recipe
# with kind carried from the launch response, analyzedRevision and
# sourceEnvironmentKey surfaced with the verdict, report gated on
# impactKnown, the never-deployed precondition on delete=false, a bounded
# consecutive Unknown retry and the truncation instruction; POWER.md names
# the precondition under Limitations; the five manifests carry one version.

set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)
POWER="$REPO_ROOT/kiro/outsystems/POWER.md"

# Lines of a doc that mention the given (case-insensitive) extended regex.
lines_matching() { # doc, regex
  grep -iE -- "$2" "$REPO_ROOT/$1" || true
}

# Body of a markdown section, heading level 2, up to the next level-2 heading.
section_body() { # file, heading text
  awk -v h="## $2" '
    $0 == h { on = 1; next }
    on && /^## / { exit }
    on { print }
  ' "$1"
}

section "every skill doc exists"
for d in "${DOCS[@]}"; do
  check_file_exists "$d exists" "$REPO_ROOT/$d"
done
check_file_absent "stale kiro steering path is not recreated" \
  "$REPO_ROOT/kiro/outsystems/steering/skill.md"

section "behaviour 1: poll passes kind returned by the launch"
for d in "${DOCS[@]}"; do
  txt=$(lines_matching "$d" 'kind')
  check_match "$d: kind is taken from the launch response" "$txt" \
    '`?kind`?[^.]*(launch|returned|start)|(launch|returned|start)[^.]*`kind`'
  check_no_match "$d: no hardcoded kind: \"deployment\" literal" "$txt" \
    'kind`?:? *`?"deployment"'
done

section "behaviour 2: analyzedRevision / sourceEnvironmentKey carried and surfaced"
for d in "${DOCS[@]}"; do
  txt=$(lines_matching "$d" 'analyzedRevision')
  check_match "$d: mentions analyzedRevision" "$txt" 'analyzedRevision'
  check_match "$d: analyzedRevision and sourceEnvironmentKey on the same line" "$txt" \
    'sourceEnvironmentKey'
  check_match "$d: kept from the launch response" "$txt" '(launch|start)'
  check_match "$d: surfaced to the user with the verdict" "$txt" \
    '(verdict|tell|report|user)'
done

section "behaviour 3: report gated on impactKnown"
for d in "${DOCS[@]}"; do
  txt=$(lines_matching "$d" 'impactKnown')
  check_match "$d: mentions impactKnown" "$txt" 'impactKnown'
  check_match "$d: report read only once impactKnown is true" "$txt" \
    'impactKnown`?[^.]*true|true[^.]*impactKnown'
  check_match "$d: gate names report" "$txt" 'report'
  check_match "$d: false means impact not (yet) known" "$txt" \
    'not( yet)? known'
done

section "R10: terminal processStatus with impactKnown false stops and reports not known"
for d in "${DOCS[@]}"; do
  txt=$(cat "$REPO_ROOT/$d")
  check_match "$d: names Finished and Failed as terminal" "$txt" \
    'Finished`?[^.]*Failed|Failed`?[^.]*Finished'
  check_match "$d: names processStatus" "$txt" 'processStatus'
done

section "R9: Unknown status retried at most 3 more consecutive times"
for d in "${DOCS[@]}"; do
  txt=$(lines_matching "$d" 'Unknown')
  check_match "$d: Unknown bounded to 3 more polls" "$txt" \
    '(3|three) more (poll|time|attempt)'
  check_match "$d: Unknown count restarts on any other status" "$txt" \
    '(restart|reset)[a-z]* (that|the) count whenever a poll returns any other status'
done

section "R11: truncation instruction without the 200 number"
for d in "${DOCS[@]}"; do
  txt=$(cat "$REPO_ROOT/$d")
  check_match "$d: names report.total" "$txt" 'report\.total'
  check_match "$d: names report.truncated" "$txt" 'report\.truncated'
  rec=$(lines_matching "$d" '(impactKnown|report\.t|impactedAssets)')
  check_no_match "$d: recipe does not restate the 200 cap" "$rec" '\b200\b'
done

section "out of scope: verdict enum values are not restated"
for d in "${DOCS[@]}"; do
  check_no_match "$d: no NoIssuesFound/WarningsFound/ErrorsFound" \
    "$(cat "$REPO_ROOT/$d")" 'NoIssuesFound|WarningsFound|ErrorsFound'
done

section "precondition on delete=false"
for d in "${DOCS[@]}"; do
  txt=$(cat "$REPO_ROOT/$d")
  check_match "$d: states the never-deployed precondition" "$txt" \
    '(never (been )?(deployed|published)|not (yet )?(been )?deployed|no deployment|deployed somewhere)'
  check_match "$d: delete=true reserved for a deletion intent" "$txt" \
    'delete`?( ?[=:] ?|: )`?true[^.]*(delet|remov)|(deletion|delet(e|ing) intent)[^.]*delete`?( ?[=:] ?|: )`?true'
  check_match "$d: delete=true is not a way around the precondition (R5)" "$txt" \
    '(not|never) (switch|fall back|use)[^.]*delete`?( ?[=:] ?|: )`?true'
  check_match "$d: asks the user before publishing (R6)" \
    "$(lines_matching "$d" 'publish')" '(ask|confirm)[^.]*publish|publish[^.]*(ask|confirm)'
  check_match "$d: development-environment publish satisfies it (R7)" \
    "$(lines_matching "$d" '(deployed|publish)')" 'development'
  lib=$(lines_matching "$d" 'LowCodeLibrary')
  for t in Workflow ExtensionLibrary LowCodeLibrary WidgetLibrary MobileLibrary; do
    check_match "$d: R16 names $t as never analysable" "$lib" "$t"
  done
  check_match "$d: unanalysable asset still gets deploy confirmation" "$lib" '(ask|confirm)[^.]*no impact analysis is available'
done

section "precondition in the confirm-before-mutation Rules bullet (R12)"
for d in "${DOCS[@]}"; do
  rules=$(section_body "$REPO_ROOT/$d" Rules)
  check_match "$d: Rules section mentions the precondition" "$rules" \
    '(never (been )?(deployed|published)|not (yet )?(been )?deployed|no deployment|deployed somewhere)'
done

section "lockstep: recipe wording byte-identical across the five docs (R2/R15)"
for pat in impactKnown analyzedRevision LowCodeLibrary 'report\.truncated'; do
  ref=$(grep -E -- "$pat" "$REPO_ROOT/${DOCS[1]}" | sort)
  for d in "${DOCS[@]}"; do
    got=$(grep -E -- "$pat" "$REPO_ROOT/$d" | sort)
    check "$d: lines with $pat identical to ${DOCS[1]}" "$got" "$ref"
  done
done
for pat in impactKnown analyzedRevision sourceEnvironmentKey; do
  ref=$(grep -c -- "$pat" "$REPO_ROOT/${DOCS[0]}")
  for d in "${DOCS[@]}"; do
    check "$d: count of $pat equals root" "$(grep -c -- "$pat" "$REPO_ROOT/$d")" "$ref"
  done
done

section "POWER.md Limitations carries the precondition (R14)"
lim=$(section_body "$POWER" Limitations)
check_match "POWER.md Limitations names deploy impact" "$lim" '(deploy_impact|impact)'
check_match "POWER.md Limitations names the never-deployed precondition" "$lim" \
  '(never (been )?(deployed|published)|not (yet )?(been )?deployed|no deployment|deployed somewhere|publish)'

section "manifests carry one version (R13)"
v1=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json")
v2=$(jq -r '.plugins[0].version' "$REPO_ROOT/.claude-plugin/marketplace.json")
v3=$(jq -r .version "$REPO_ROOT/cursor/.cursor-plugin/plugin.json")
v4=$(jq -r '.plugins[0].version' "$REPO_ROOT/.cursor-plugin/marketplace.json")
v5=$(jq -r .version "$REPO_ROOT/kiro/outsystems/plugin.json")
check "claude marketplace version matches plugin" "$v2" "$v1"
check "cursor plugin version matches" "$v3" "$v1"
check "cursor marketplace version matches" "$v4" "$v1"
check "kiro plugin version matches" "$v5" "$v1"

finish
