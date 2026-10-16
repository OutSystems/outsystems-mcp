#!/usr/bin/env bash
# Every file that carries the plugin version agrees with
# `claude/.claude-plugin/plugin.json`: the five manifests, and the
# `X-OutSystems-Plugin-Version` header value in the five files that set it
# as a literal. The Claude plugin sets no literal: the `headersHelper` of
# `claude/.mcp.json` runs a script that reads the version from
# `plugin.json`. The suite runs that command the way Claude Code does, and
# runs each script on copies of `plugin.json` in other layouts.
# CONTRIBUTING.md "Versioning and Releases" lists those files. The source
# value must be SemVer 2.0 and at most 64 bytes, because the MCP server
# applies the same rule to the header it receives. A new manifest fails the
# suite, and so does a file other than those and the two scripts where the
# header name, in any letter case and optionally quoted, is followed by `:`
# or `=`.

set -uo pipefail
# A caller's environment must not point the git calls at another repository.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
export LC_ALL=C

command -v jq >/dev/null || { echo "missing prerequisite: jq" >&2; exit 1; }
command -v git >/dev/null || { echo "missing prerequisite: git" >&2; exit 1; }

# The semver.org regex in POSIX ERE: `\d` -> `[0-9]`, `(?:` -> `(`.
SEMVER='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-(0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*)?(\+[0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*)?$'

SOURCE=claude/.claude-plugin/plugin.json
PLUGINS=(cursor/.cursor-plugin/plugin.json kiro/outsystems/plugin.json)
MARKETPLACES=(.claude-plugin/marketplace.json .cursor-plugin/marketplace.json)
HEADER_JSON=(cursor/mcp.json)
CLAUDE_MCP=claude/.mcp.json
HELPERS=(claude/scripts/plugin-version-header.sh claude/scripts/plugin-version-header.ps1)
PS_ARGS=(-NoProfile -NonInteractive -ExecutionPolicy Bypass -File)
HELPER_CMD="sh \"\${CLAUDE_PLUGIN_ROOT}/${HELPERS[0]#claude/}\" || powershell ${PS_ARGS[*]} \"\${CLAUDE_PLUGIN_ROOT}/${HELPERS[1]#claude/}\""
HEADER_MD=(
  cursor/skills/outsystems/SKILL.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/README.md
  README.md
)

# Built from parts so that this file never carries the shapes it looks for.
# `shape` is the JSON key with its opening value quote. `key` is the name in
# any letter case as a key in any syntax, with the value on the same line or
# the next. Prose that names the header matches neither.
name=X-OutSystems-Plugin-Version
shape="\"$name\":[[:space:]]*\""
key="[\"']?${name}[\"']?[[:space:]]*[:=]"

# Runs a boolean jq filter, with `$s` bound to the JSON-encoded source value
# and `$h` to the header name. Every comparison with the source happens in
# jq, because `$(...)` strips trailing newlines and a shell comparison would
# accept a consumer value of "1.8.0\n".
jq_true() { # file or "-" for stdin, filter
  jq -e --argjson s "$srcjson" --arg h "$name" "$2" "$1" >/dev/null 2>&1 && echo yes
}

# The raw JSON string literals of the header values a Markdown file sets,
# one per line.
md_literals() { # file
  grep -oE "${shape}[^\"]*\"" "$1" | sed -E "s/^\"$name\":[[:space:]]*//"
}

# The server entry that holds each header the Markdown file sets, one per
# line: the last `"<key>": {` other than `headers`, or `mcpServers.<key>`,
# before the header.
md_servers() { # file
  awk -v key="\"$name\":" '
    { text = text $0 "\n" }
    END {
      rest = text
      while ((i = index(rest, key)) > 0) {
        before = substr(rest, 1, i - 1)
        while (match(before, /"[^"]+":[[:space:]]*[{]|mcpServers[.][A-Za-z0-9_-]+/)) {
          tok = substr(before, RSTART, RLENGTH)
          before = substr(before, RSTART + RLENGTH)
          if (tok ~ /^mcpServers/) {
            server = substr(tok, 12)
          } else {
            sub(/^"/, "", tok); sub(/".*/, "", tok)
            if (tok != "headers") server = tok
          }
        }
        print server
        rest = substr(rest, i + length(key))
      }
    }' "$1"
}

# The files among the NUL-separated paths on stdin, relative to the dir,
# that set the header in any syntax.
header_files() { # dir
  local f
  while IFS= read -r -d '' f; do
    f=${f#./}
    [ -f "$1/$f" ] && grep -qiE -- "$key" "$1/$f" && echo "$f"
  done | sort
}

EVERY_KEY="every header key in any letter case, anywhere in the file"
COMPLETE="the header appears only in the listed files and the two helper files"
NO_LITERAL="$CLAUDE_MCP: no header key in any letter case"
HELPER="$CLAUDE_MCP: headersHelper runs the sh helper, and the PowerShell helper where sh fails"
MANIFESTS="the manifests are exactly the listed five"

md_expected_hits() { # file
  case "$1" in
    README.md) echo 2 ;;
    *) echo 1 ;;
  esac
}

check_root() { # dir, command that lists the files of the dir NUL-separated
  local dir=$1 list=$2 src srcjson f n v i

  section "source value"
  check "$SOURCE: version holds no newline" \
    "$(jq -e '.version | test("\n") | not' "$dir/$SOURCE" >/dev/null 2>&1 && echo yes)" yes
  src=$(jq -r .version "$dir/$SOURCE")
  srcjson=$(jq -c .version "$dir/$SOURCE")
  check "$SOURCE: version is not empty" "$([ -n "$src" ] && echo yes)" yes
  check "$SOURCE: version is at most 64 bytes" "$([ "${#src}" -le 64 ] && echo yes)" yes
  check_match "$SOURCE: version is SemVer 2.0" "$src" "$SEMVER"

  section "manifests"
  for f in "${PLUGINS[@]}"; do
    check "$f: version" "$(jq_true "$dir/$f" '.version == $s')" yes
  done
  for f in "${MARKETPLACES[@]}"; do
    n=$(jq '.plugins | length' "$dir/$f")
    check "$f: one plugin entry" "$n" 1
    for ((i = 0; i < n; i++)); do
      check "$f: plugins[$i].version" "$(jq_true "$dir/$f" ".plugins[$i].version == \$s")" yes
    done
  done

  section "header in the plugin and template configs"
  for f in "${HEADER_JSON[@]}"; do
    check "$f: outsystems header value" \
      "$(jq_true "$dir/$f" '.mcpServers.outsystems.headers[$h] == $s')" yes
    check "$f: $EVERY_KEY" \
      "$(jq_true "$dir/$f" '[.. | objects | to_entries[] | select((.key | ascii_downcase) == ($h | ascii_downcase)) | .value == $s] | all')" yes
  done

  section "header through the headersHelper of the Claude plugin"
  check "$NO_LITERAL" \
    "$(jq -e --arg h "$name" '[.. | objects | keys[] | ascii_downcase] | index($h | ascii_downcase) | not' \
      "$dir/$CLAUDE_MCP" >/dev/null 2>&1 && echo yes)" yes
  check "$HELPER" \
    "$(jq -r '.mcpServers.outsystems.headersHelper' "$dir/$CLAUDE_MCP" 2>/dev/null)" "$HELPER_CMD"

  section "header in the setup recipes"
  for f in "${HEADER_MD[@]}"; do
    check "$f: header count" "$(md_literals "$dir/$f" | wc -l | tr -d ' ')" \
      "$(md_expected_hits "$f")"
    check "$f: every header sits in the outsystems entry" \
      "$(md_servers "$dir/$f" | grep -cvx outsystems)" 0
    n=0
    while IFS= read -r v; do
      n=$((n + 1))
      check "$f: header value $n" "$(jq_true - '. == $s' <<<"$v")" yes
    done < <(md_literals "$dir/$f")
  done

  section "completeness"
  check "$COMPLETE" "$("$list" "$dir" | header_files "$dir")" \
    "$(printf '%s\n' "$expected_headers" "${HELPERS[@]}" | sort)"
}

check_manifests() { # dir, a git work tree
  check "$MANIFESTS" \
    "$(git -C "$1" ls-files '*plugin.json' '*marketplace.json' | sort)" "$expected_manifests"
}

# The PowerShell that runs the PowerShell helper here: Windows PowerShell
# where it exists, as in the headersHelper, else PowerShell 7.
PS=$(command -v powershell || command -v pwsh)
NO_PS="no powershell or pwsh on PATH"

# Prints "<exit code>|<stdout>" of one way to run the helper on the plugin
# folder. "command" is the headersHelper of the folder's .mcp.json, with
# ${CLAUDE_PLUGIN_ROOT} replaced before the shell sees it, and run under
# `sh -c` from outside the folder, as Claude Code runs it.
run_helper() { # plugin folder, sh|ps|command
  local out rc cmd
  case "$2" in
    sh) out=$(cd "$WORK" && sh "$1/scripts/plugin-version-header.sh" 2>/dev/null) ;;
    ps) out=$(cd "$WORK" && "$PS" "${PS_ARGS[@]}" "$1/scripts/plugin-version-header.ps1" 2>/dev/null) ;;
    command)
      cmd=$(jq -r '.mcpServers.outsystems.headersHelper' "$1/.mcp.json")
      out=$(cd "$WORK" && CLAUDE_PLUGIN_ROOT="$1" sh -c "${cmd//'${CLAUDE_PLUGIN_ROOT}'/$1}" 2>/dev/null)
      ;;
  esac
  rc=$?
  printf '%s|%s' "$rc" "$out"
}

# "yes" when the output is exactly one JSON object whose one key is the
# header name and whose value equals the version in the manifest.
helper_prints_version() { # manifest, output
  jq -s -e --argjson s "$(jq -c .version "$1")" --arg h "$name" \
    'length == 1 and (.[0] | type == "object" and keys == [$h] and .[$h] == $s)' \
    <<<"$2" >/dev/null 2>&1 && echo yes
}

# Runs the helper each way on the plugin folder. With "fails", each way must
# exit non-zero and print nothing; else each must print the version.
check_helpers() { # plugin folder, case title, [fails]
  local way r
  for way in command sh ps; do
    if [ "$way" = ps ] && [ -z "$PS" ]; then
      _report 0 "$2: the ps helper # SKIP $NO_PS"
      continue
    fi
    r=$(run_helper "$1" "$way")
    if [ "${3:-}" = fails ]; then
      check "$2: the $way helper exits non-zero and prints nothing" \
        "$([ "${r%%|*}" != 0 ] && echo fail)|${r#*|}" "fail|"
    else
      check "$2: the $way helper prints the version" \
        "${r%%|*}|$(helper_prints_version "$1/.claude-plugin/plugin.json" "${r#*|}")" "0|yes"
    fi
  done
}

tracked_files() { git -C "$1" ls-files -z; }
all_files() { (cd "$1" && find . -type f -print0); }

expected_headers=$(printf '%s\n' "${HEADER_JSON[@]}" "${HEADER_MD[@]}" | sort)
expected_manifests=$(printf '%s\n' "$SOURCE" "${PLUGINS[@]}" "${MARKETPLACES[@]}" | sort)
before=$_checks
check_root "$REPO_ROOT" tracked_files
all_checks=$((_checks - before))
check_manifests "$REPO_ROOT"
section "the headersHelper of the Claude plugin"
check_helpers "$REPO_ROOT/claude" "the repository"

section "self-test: each mutation fails exactly the checks it targets"
ALL=("$SOURCE" "${PLUGINS[@]}" "${MARKETPLACES[@]}" "${HEADER_JSON[@]}" "${HEADER_MD[@]}"
  "$CLAUDE_MCP" "${HELPERS[@]}")
MUT="$WORK/mut"
PRISTINE="$WORK/pristine"
for f in "${ALL[@]}"; do
  mkdir -p "$PRISTINE/$(dirname "$f")"
  cp "$REPO_ROOT/$f" "$PRISTINE/$f"
done

restore() { rm -rf "$MUT"; cp -R "$PRISTINE" "$MUT"; }
TAB=$'\t'

src=$(jq -r .version "$PRISTINE/$SOURCE")
# The source value with its first character moved by one digit: valid
# SemVer of the same length, and never equal to the source value.
case "${src:0:1}" in
  [0-8]) drift="$((${src:0:1} + 1))${src:1}" ;;
  *) drift="8${src:1}" ;;
esac

# The report of the command, run with fresh counters.
run_checks() { # command...
  ( _checks=0; _failures=0; "$@" 2>/dev/null )
}

# The names of the checks that failed in the report, sorted, one per line.
failed_checks() { # report
  printf '%s\n' "$1" | sed -n 's/^not ok [0-9]* - //p' | sort
}

check_count() { # report
  printf '%s\n' "$1" | grep -cE '^(not )?ok [0-9]+ - '
}

# Runs every check on the mutated copy, then restores it. The checks that
# fail must be exactly the named ones. With no names, every check passes,
# and as many checks run as on the repository.
expect_failure() { # mutation, check names...
  local want="" title="self-test: $1 passes" out
  if [ $# -gt 1 ]; then
    want=$(printf '%s\n' "${@:2}" | sort)
    title="self-test: $1 fails only the targeted checks"
  fi
  out=$(run_checks check_root "$MUT" all_files)
  check "$title" "$(failed_checks "$out")" "$want"
  if [ $# -eq 1 ]; then
    check "self-test: $1 runs every check" "$(check_count "$out")" "$all_checks"
  fi
  restore
}

jq_edit() { # file, jq args...
  local f=$MUT/$1; shift
  jq "$@" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

sed_edit() { # file, sed script
  sed "$2" "$MUT/$1" > "$MUT/$1.tmp" && mv "$MUT/$1.tmp" "$MUT/$1"
}

sed_escape() { printf '%s' "$1" | sed 's/[\\&|]/\\&/g'; }

# Writes the value into all ten files. Every equality check then
# passes, so only the source-value checks can fail.
set_everywhere() { # value
  local f quoted
  jq_edit "$SOURCE" --arg v "$1" '.version = $v'
  for f in "${PLUGINS[@]}"; do jq_edit "$f" --arg v "$1" '.version = $v'; done
  for f in "${MARKETPLACES[@]}"; do jq_edit "$f" --arg v "$1" '.plugins[0].version = $v'; done
  for f in "${HEADER_JSON[@]}"; do
    jq_edit "$f" --arg h "$name" --arg v "$1" '.mcpServers.outsystems.headers[$h] = $v'
  done
  quoted=$(sed_escape "$(jq -n --arg v "$1" '$v')")
  for f in "${HEADER_MD[@]}"; do
    sed_edit "$f" "s|\"$name\":[[:space:]]*\"[^\"]*\"|\"$name\": $quoted|g"
  done
}

NEWLINE="$SOURCE: version holds no newline"
NONEMPTY="$SOURCE: version is not empty"
LENGTH="$SOURCE: version is at most 64 bytes"
SEMVER_CHECK="$SOURCE: version is SemVer 2.0"

# The checks of the header values a Markdown file sets, one per line.
md_value_checks() { # file
  local n
  for ((n = 1; n <= $(md_expected_hits "$1"); n++)); do echo "$1: header value $n"; done
}

# Every check that compares a value with the source value.
VALUE_CHECKS=()
for f in "${PLUGINS[@]}"; do VALUE_CHECKS+=("$f: version"); done
for f in "${MARKETPLACES[@]}"; do VALUE_CHECKS+=("$f: plugins[0].version"); done
for f in "${HEADER_JSON[@]}"; do
  VALUE_CHECKS+=("$f: outsystems header value" "$f: $EVERY_KEY")
done
for f in "${HEADER_MD[@]}"; do VALUE_CHECKS+=("$(md_value_checks "$f")"); done

restore
expect_failure "the unmutated copy"

jq_edit "$SOURCE" --arg d "$drift" '.version = $d'
expect_failure "$SOURCE: changed version" "${VALUE_CHECKS[@]}"
sed_edit "$SOURCE" '$d'
expect_failure "$SOURCE: corrupt JSON" "$NEWLINE" "$NONEMPTY" "$SEMVER_CHECK" "${VALUE_CHECKS[@]}"
for f in "${PLUGINS[@]}"; do
  jq_edit "$f" --arg d "$drift" '.version = $d'
  expect_failure "$f: changed version" "$f: version"
  sed_edit "$f" '$d'
  expect_failure "$f: corrupt JSON" "$f: version"
done
for f in "${MARKETPLACES[@]}"; do
  jq_edit "$f" --arg d "$drift" '.plugins[0].version = $d'
  expect_failure "$f: changed version" "$f: plugins[0].version"
  jq_edit "$f" --arg d "$drift" '.plugins += [.plugins[0] + {version: $d}]'
  expect_failure "$f: second plugin entry with another version" \
    "$f: one plugin entry" "$f: plugins[1].version"
  sed_edit "$f" '$d'
  expect_failure "$f: corrupt JSON" "$f: one plugin entry"
done
for f in "${HEADER_JSON[@]}"; do
  jq_edit "$f" --arg h "$name" --arg d "$drift" '.mcpServers.outsystems.headers[$h] = $d'
  expect_failure "$f: changed header value" "$f: outsystems header value" "$f: $EVERY_KEY"
  jq_edit "$f" 'del(.mcpServers.outsystems.headers)'
  expect_failure "$f: header removed" "$f: outsystems header value" "$COMPLETE"
  jq_edit "$f" --arg h "$name" --arg d "$drift" \
    '.mcpServers.other = {url: "https://example.invalid/mcp", headers: {($h): $d}}'
  expect_failure "$f: second server entry with another header value" "$f: $EVERY_KEY"
  jq_edit "$f" --arg h "$name" --arg d "$drift" \
    '.mcpServers.outsystems.headers[$h | ascii_downcase] = $d'
  expect_failure "$f: lowercase duplicate with another header value" "$f: $EVERY_KEY"
  jq_edit "$f" --arg h "$name" --arg d "$drift" '.other = {headers: {($h): $d}}'
  expect_failure "$f: header with another value outside mcpServers" "$f: $EVERY_KEY"
  jq_edit "$f" '.mcpServers |= [.]'
  expect_failure "$f: mcpServers as an array" "$f: outsystems header value"
  sed_edit "$f" '$d'
  expect_failure "$f: corrupt JSON" "$f: outsystems header value" "$f: $EVERY_KEY"
done
jq_edit "$CLAUDE_MCP" --arg h "$name" --arg v "$src" '.mcpServers.outsystems.headers = {($h): $v}'
expect_failure "$CLAUDE_MCP: literal header" "$NO_LITERAL" "$COMPLETE"
jq_edit "$CLAUDE_MCP" --arg h "$name" --arg v "$src" '.other = {headers: {($h | ascii_downcase): $v}}'
expect_failure "$CLAUDE_MCP: lowercase literal header outside mcpServers" "$NO_LITERAL" "$COMPLETE"
jq_edit "$CLAUDE_MCP" 'del(.mcpServers.outsystems.headersHelper)'
expect_failure "$CLAUDE_MCP: headersHelper removed" "$HELPER"
jq_edit "$CLAUDE_MCP" '.mcpServers.outsystems.headersHelper |= sub(" [|][|] .*"; "")'
expect_failure "$CLAUDE_MCP: headersHelper without the PowerShell helper" "$HELPER"
sed_edit "$CLAUDE_MCP" '$d'
expect_failure "$CLAUDE_MCP: corrupt JSON" "$NO_LITERAL" "$HELPER"

for f in "${HEADER_MD[@]}"; do
  # Each edit changes the first header of every line, so it reaches every
  # header of the file.
  values=$(md_value_checks "$f")
  sed_edit "$f" "s|\\($shape\\)[^\"]*\"|\\1$(sed_escape "$drift")\"|"
  expect_failure "$f: changed header value" "$values"
  sed_edit "$f" "s|${shape}[^\"]*\"||"
  expect_failure "$f: header removed" "$f: header count" "$COMPLETE"
  sed_edit "$f" "s|\"$name\":[[:space:]]*\"[^\"]*\"|\"$name\":$TAB\"$(sed_escape "$drift")\"|"
  expect_failure "$f: tab before a changed header value" "$values"
  sed_edit "$f" 's/"outsystems":/"other":/g; s/mcpServers[.]outsystems/mcpServers.other/g'
  expect_failure "$f: header in another server entry" "$f: every header sits in the outsystems entry"
done

# A new file that sets the header with the current value.
lower=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')
printf '{"%s": "%s"}\n' "$lower" "$src" > "$MUT/new.json"
expect_failure "new file with the header name in lowercase" "$COMPLETE"
printf '{"%s" : "%s"}\n' "$name" "$src" > "$MUT/new.json"
expect_failure "new file with a space before the colon" "$COMPLETE"
printf '{"%s":\n  "%s"}\n' "$name" "$src" > "$MUT/new.json"
expect_failure "new file with the value on the next line" "$COMPLETE"
printf '[headers]\n"%s" = "%s"\n' "$name" "$src" > "$MUT/new.toml"
expect_failure "new TOML file" "$COMPLETE"

# A trailing newline in one consumer value.
for f in "${PLUGINS[@]}"; do
  jq_edit "$f" --arg v "$src"$'\n' '.version = $v'
  expect_failure "$f: version with a trailing newline" "$f: version"
done
for f in "${MARKETPLACES[@]}"; do
  jq_edit "$f" --arg v "$src"$'\n' '.plugins[0].version = $v'
  expect_failure "$f: version with a trailing newline" "$f: plugins[0].version"
done
for f in "${HEADER_JSON[@]}"; do
  jq_edit "$f" --arg h "$name" --arg v "$src"$'\n' '.mcpServers.outsystems.headers[$h] = $v'
  expect_failure "$f: header value with a trailing newline" \
    "$f: outsystems header value" "$f: $EVERY_KEY"
done
for f in "${HEADER_MD[@]}"; do
  sed_edit "$f" "s|\\($shape\\)[^\"]*\"|\\1$(sed_escape "$src")\\\\n\"|"
  expect_failure "$f: header value with a trailing newline" "$(md_value_checks "$f")"
done

for f in "${HEADER_MD[@]}"; do
  sed_edit "$f" "s|\"$name\":[[:space:]]*\"|\"$name\":$TAB\"|"
  expect_failure "$f: tab before the header value"
  awk '{ printf "%s\r\n", $0 }' "$MUT/$f" > "$MUT/$f.tmp" && mv "$MUT/$f.tmp" "$MUT/$f"
  expect_failure "$f: CRLF line endings"
done

long="1.0.0-$(printf 'a%.0s' $(seq 58))"
for v in "$long" "1.0.0-rc.1+build.5" "1.0.0+20130313144700"; do
  set_everywhere "$v"
  expect_failure "valid source value $(jq -n --arg v "$v" '$v') in all ten files"
done

set_everywhere ""
expect_failure 'empty source value "" in all ten files' "$NONEMPTY" "$SEMVER_CHECK"
set_everywhere "${long}a"
expect_failure "source value of 65 bytes in all ten files" "$LENGTH"
set_everywhere $'1.7.1\n'
expect_failure 'source value "1.7.1\n" in all ten files' "$NEWLINE"
for v in "1.7" "1.0.0-01" "v1.0.0" "01.0.0" "1.0.0+" "1.0.0-a..b"; do
  set_everywhere "$v"
  expect_failure "invalid source value \"$v\" in all ten files" "$SEMVER_CHECK"
done

section "self-test: the helpers read plugin.json in any layout"
# The space in the path checks the quotes of the headersHelper.
HH="$WORK/helper copy/claude"
mkdir -p "$HH/.claude-plugin"
cp -R "$REPO_ROOT/claude/scripts" "$REPO_ROOT/$CLAUDE_MCP" "$HH/"
MANIFEST="$HH/.claude-plugin/plugin.json"
manifest_case() { # case title, [fails], jq filter
  jq "${@:3}" "$PRISTINE/$SOURCE" > "$MANIFEST"
  check_helpers "$HH" "$1" "${2:-}"
}
manifest_case "two-space indent" "" .
manifest_case "one line" "" -c .
manifest_case "tab indent" "" --tab .
manifest_case "four-space indent" "" --indent 4 .
manifest_case "version as the last key" "" 'del(.version) + {version}'
manifest_case "nested version key first" "" '{a: {version: "0.0.1"}} + .'
manifest_case "string \"version\" first" "" '{a: ["version"], b: "version"} + .'
manifest_case "\"}\" in a string before a nested version key" "" '{a: "}", b: {version: "0.0.1"}} + .'
manifest_case "\"{\" in a string before the version key" "" '{a: "{"} + .'
manifest_case "escaped quotes and backslashes in strings" "" \
  '{a: "\"}\\", b: "x\\\\", c: "\"version\": \"0.0.1\"", d: {version: "0.0.1"}} + .'
jq . "$PRISTINE/$SOURCE" | awk '{ printf "%s\r\n", $0 }' > "$MANIFEST"
check_helpers "$HH" "CRLF line endings"
printf '%s' "$(jq -c . "$PRISTINE/$SOURCE")" > "$MANIFEST"
check_helpers "$HH" "no newline at the end"
jq '.version' "$PRISTINE/$SOURCE" | { printf '{\n  "version":\n    '; cat; printf '}\n'; } > "$MANIFEST"
check_helpers "$HH" "version value on the next line"
manifest_case "version removed" fails 'del(.version)'
manifest_case "empty version" fails '.version = ""'
manifest_case "version as a number" fails '.version = 1'
manifest_case "nested version key only" fails '{a: {version}} + del(.version)'
manifest_case "top-level array" fails '[.]'

# The helpers print only a value whose characters are all SemVer
# characters. The character check alone rejects the first five cases.
GATE_ONLY=("backslash" "escaped CR" "escaped LF" "non-ASCII" "raw CR")
GATE_VALUES=('1.0.0\x' $'1.0.0\rx' $'1.0.0\nx' $'1.0.0-\xc3\xa9')
reject_cases() { # plugin folder
  local i plugin=$1/.claude-plugin/plugin.json
  for i in "${!GATE_VALUES[@]}"; do
    jq --arg v "${GATE_VALUES[$i]}" '.version = $v' "$PRISTINE/$SOURCE" > "$plugin"
    check_helpers "$1" "${GATE_ONLY[$i]} in the version" fails
  done
  printf '{"version": "1.0.0\rx"}\n' > "$plugin"
  check_helpers "$1" "${GATE_ONLY[4]} in the version" fails
  jq --arg v '1.0.0"x' '.version = $v' "$PRISTINE/$SOURCE" > "$plugin"
  check_helpers "$1" "quote in the version" fails
  printf '{"version": "1.0.0\nx"}\n' > "$plugin"
  check_helpers "$1" "raw LF in the version" fails
}
reject_cases "$HH"

# The same cases on a copy of the sh helper without the character check:
# each case the check alone rejects must then fail in the sh helper and in
# the command that runs it.
NOGATE="$WORK/no gate/claude"
mkdir -p "$NOGATE/.claude-plugin"
cp -R "$HH/scripts" "$HH/.mcp.json" "$NOGATE/"
sed 's/^  "" | \*\[!0-9A-Za-z.+-\]\*) exit 1 ;;$/  "") exit 1 ;;/' \
  "$HH/scripts/plugin-version-header.sh" > "$NOGATE/scripts/plugin-version-header.sh"
want=$(for c in "${GATE_ONLY[@]}"; do
  for way in command sh; do echo "$c in the version: the $way helper exits non-zero and prints nothing"; done
done | sort)
check "self-test: the sh helper without the character check fails only the targeted checks" \
  "$(failed_checks "$(run_checks reject_cases "$NOGATE")")" "$want"

# A large manifest, with braces, quotes and backslashes in its strings,
# must stay far below the 10-second limit of Claude Code.
jq '{a: [range(3000) | {version: "0.0.1", k: "}{\"\\"}]} + .' "$PRISTINE/$SOURCE" > "$MANIFEST"
start=$SECONDS
r=$(run_helper "$HH" sh)
check "3000 objects: the sh helper prints the version in under 10 s" \
  "${r%%|*}|$((SECONDS - start < 10))" "0|1"
check_helpers "$HH" "3000 objects"

section "self-test: the git listings"
GITREPO=$(mktemp -d "$WORK/git.XXXXXX")
cp -R "$PRISTINE/." "$GITREPO"
git -C "$GITREPO" init -q
git -C "$GITREPO" add -A
out=$(run_checks check_root "$GITREPO" tracked_files)
check "self-test: the unmutated git copy passes" \
  "$(failed_checks "$out"; failed_checks "$(run_checks check_manifests "$GITREPO")")" ""
check "self-test: the unmutated git copy runs every check" "$(check_count "$out")" "$all_checks"
printf '{"%s": "%s"}\n' "$name" "$src" > "$GITREPO/new.json"
git -C "$GITREPO" add new.json
check "self-test: a tracked new file with the header fails only the targeted checks" \
  "$(failed_checks "$(run_checks check_root "$GITREPO" tracked_files)")" "$COMPLETE"
mkdir "$GITREPO/x"
cp "$PRISTINE/${PLUGINS[0]}" "$GITREPO/x/plugin.json"
git -C "$GITREPO" add x/plugin.json
check "self-test: a sixth tracked manifest fails only the targeted checks" \
  "$(failed_checks "$(run_checks check_manifests "$GITREPO")")" "$MANIFESTS"

section "self-test: prerequisites"
# PATH holds links to the tools the suite calls before its jq check, and
# no jq, so the suite must stop at that check.
NOJQ="$WORK/nojq"
mkdir "$NOJQ"
for tool in bash dirname mktemp mkdir rm; do
  ln -s "$(command -v "$tool")" "$NOJQ/$tool"
done
out=$(PATH="$NOJQ" "$NOJQ/bash" "$TESTS_DIR/plugin-version-lockstep.test.sh" 2>&1)
rc=$?
check "self-test: the suite exits 1 without jq" "$rc" 1
check_match "self-test: the suite names jq as missing" "$out" "missing prerequisite: jq"

finish
