#!/usr/bin/env bash
# Runs every suite in this directory. No GitHub Actions workflow invokes
# it: run it locally before pushing a change to `ai-review.yml`, whose
# shell steps only ever execute on a privileged runner otherwise.
#
# Needs: bash, git, jq, python3 with PyYAML.

set -uo pipefail
cd "$(dirname "$0")" || exit 1

for tool in git jq python3; do
  command -v "$tool" >/dev/null || { echo "missing prerequisite: $tool" >&2; exit 1; }
done
python3 -c 'import yaml' 2>/dev/null || {
  echo "missing prerequisite: python3 PyYAML (pip install pyyaml)" >&2
  exit 1
}

rc=0
for suite in ./*.test.sh; do
  printf '=== %s\n' "${suite#./}"
  bash "$suite" || rc=1
  printf '\n'
done

if [ "$rc" -eq 0 ]; then echo "all suites passed"; else echo "SUITES FAILED"; fi
exit "$rc"
