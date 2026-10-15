#!/usr/bin/env bash
# The platform check for customers who connect both the OutSystems 11 (O11)
# and the ODC MCP servers. Pins:
# - the "Platform first" Rules bullet: once in each of the five lockstepped
#   skill docs and byte-identical across them, and the feedback Scope
#   sentence that leaves out the O11 server;
# - the main skill description (claude, cursor, kiro), identical in the three,
#   and the O11 exclusion at the end of each Beta skill description (the
#   Cursor and Kiro copies of the Beta skills are covered by
#   tests/skills/test_harness_copies.py);
# - the README recipes that add this skill to an existing O11 instructions
#   file: the check order, the git-tracked check, and the byte-exact append
#   and replace commands, which must not drift from the versions tested
#   against real O11 files in bash and PowerShell.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

MAIN_DESCRIBED=(
  claude/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
  kiro/outsystems/skills/outsystems/SKILL.md
)

BETA_DESCRIBED=(
  claude/skills/outsystems-app-architecture/SKILL.md
  claude/skills/outsystems-dependency-impact/SKILL.md
  claude/skills/outsystems-design-to-app/SKILL.md
  claude/skills/outsystems-spec-driven-build/SKILL.md
  claude/skills/outsystems-tenant-architecture/SKILL.md
)

count() { # fixed string, file -> number of occurrences
  grep -oF -- "$1" "$2" | wc -l | tr -d ' '
}

first_rule_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  rule=$(grep -F -- '- **Platform first.**' "$REPO_ROOT/$doc")
  check "has the Platform first rule once" "$(printf '%s\n' "$rule" | grep -c .)" 1
  check_match "names the O11 server by role, not only by name" "$rule" 'the Service Studio MCP server \(named `servicestudio` in the O11 setup\)'
  check_match "asks when the platform is unclear" "$rule" 'Is this for ODC, or for the O11 module open in Service Studio\?'
  check_match "stops when the O11 server is missing" "$rule" 'start the MCP server in Service Studio and stop'
  check_match "keeps the platform for later requests" "$rule" 'treat later requests in this conversation as for that platform unless the user says otherwise\.$'
  scope=$(grep -F -- '**Scope.**' "$REPO_ROOT/$doc")
  check "has one feedback Scope line" "$(printf '%s\n' "$scope" | grep -c .)" 1
  check_match "feedback Scope leaves out the O11 server" "$scope" 'Tools from the Service Studio MCP server \(named `servicestudio` in the O11 setup\) belong to OutSystems 11 \(O11\): never report on them\.'
  rule_hash=$(printf '%s' "$rule" | git hash-object --stdin)
  if [ -z "$rule_hash" ]; then
    echo "git hash-object returned nothing for $doc" >&2
    exit 1
  fi
  [ -n "$first_rule_hash" ] || first_rule_hash=$rule_hash
  check "Platform first rule is byte-identical to ${DOCS[0]}" "$rule_hash" "$first_rule_hash"
done

section "skill descriptions"
main_description='description: "OutSystems Developer Cloud (ODC) over MCP. Edit apps, publish, deploy, search tenant elements, manage external libraries. Use for ANY OutSystems task on ODC. Not for OutSystems 11 (O11) modules open in Service Studio."'
for doc in "${MAIN_DESCRIBED[@]}"; do
  check "$doc names ODC and rules out O11" "$(grep -m1 '^description: ' "$REPO_ROOT/$doc")" "$main_description"
done
for doc in "${BETA_DESCRIBED[@]}"; do
  check_match "$doc ends by ruling out O11" "$(grep -m1 '^description: ' "$REPO_ROOT/$doc")" "Not for OutSystems 11 \(O11\) or Service Studio\.[\"']$"
done

# The commands below are the README text verbatim; F and U are the
# placeholders the agent fills with the file's path and the skill URL.
# `read` already strips the heredoc's final newline under the default IFS;
# each `${VAR%$'\n'}` keeps the value one line even if IFS changes, since a
# newline would split the `grep -F` pattern in `count`.
read -r -d '' BASH_APPEND <<'EOF'
t=$(mktemp) && curl -fsSL U -o "$t" && { [ -z "$(tail -c1 F)" ] || echo >> F; cat "$t" >> F; }
EOF
BASH_APPEND=${BASH_APPEND%$'\n'}
read -r -d '' PS_APPEND <<'EOF'
& { $ErrorActionPreference='Stop'; $t=(New-TemporaryFile).FullName; Invoke-WebRequest -UseBasicParsing -Uri U -OutFile $t; $d=(Resolve-Path F).Path; $nl=([IO.File]::ReadAllBytes($d)[-1] -ne 10); $b=[IO.File]::ReadAllBytes($t); $f=[IO.File]::Open($d,'Append'); if($nl){$f.WriteByte(10)}; $f.Write($b,0,$b.Length); $f.Close() }
EOF
PS_APPEND=${PS_APPEND%$'\n'}
read -r -d '' BASH_REPLACE_HEADING <<'EOF'
t=$(mktemp) && curl -fsSL U -o "$t" && o=$(LC_ALL=C grep -b -m1 -x '# OutSystems - Remote MCP' F | cut -d: -f1) && [ -n "$o" ] && { head -c "$o" F; cat "$t"; } > "$t.new" && cat "$t.new" > F
EOF
BASH_REPLACE_HEADING=${BASH_REPLACE_HEADING%$'\n'}
read -r -d '' BASH_REPLACE_FRONTMATTER <<'EOF'
t=$(mktemp) && curl -fsSL U -o "$t" && n=$(LC_ALL=C grep -b -m1 -x 'name: outsystems' F | cut -d: -f1) && [ -n "$n" ] && o=$((n-4)) && [ "$(tail -c +$((o+1)) F | head -n1)" = '---' ] && { head -c "$o" F; cat "$t"; } > "$t.new" && cat "$t.new" > F
EOF
BASH_REPLACE_FRONTMATTER=${BASH_REPLACE_FRONTMATTER%$'\n'}
read -r -d '' PS_REPLACE_HEADING <<'EOF'
& { $ErrorActionPreference='Stop'; $t=(New-TemporaryFile).FullName; Invoke-WebRequest -UseBasicParsing -Uri U -OutFile $t; $d=(Resolve-Path F).Path; $a=[IO.File]::ReadAllBytes($d); $n=[string][char]10; $i=[Text.Encoding]::GetEncoding(28591).GetString($a).IndexOf($n+'# OutSystems - Remote MCP'+$n,[StringComparison]::Ordinal); if($i -lt 0){throw 'marker not found'}; [IO.File]::WriteAllBytes($d,[byte[]]($a[0..$i]+[IO.File]::ReadAllBytes($t))) }
EOF
PS_REPLACE_HEADING=${PS_REPLACE_HEADING%$'\n'}
read -r -d '' PS_REPLACE_FRONTMATTER <<'EOF'
& { $ErrorActionPreference='Stop'; $t=(New-TemporaryFile).FullName; Invoke-WebRequest -UseBasicParsing -Uri U -OutFile $t; $d=(Resolve-Path F).Path; $a=[IO.File]::ReadAllBytes($d); $n=[string][char]10; $i=[Text.Encoding]::GetEncoding(28591).GetString($a).IndexOf($n+'---'+$n+'name: outsystems'+$n,[StringComparison]::Ordinal); if($i -lt 0){throw 'marker not found'}; [IO.File]::WriteAllBytes($d,[byte[]]($a[0..$i]+[IO.File]::ReadAllBytes($t))) }
EOF
PS_REPLACE_FRONTMATTER=${PS_REPLACE_FRONTMATTER%$'\n'}

README="$REPO_ROOT/README.md"
section "README: adding the skill to an O11 instructions file"
# Four recipes write an instructions file: Copilot in VS Code, Copilot in
# CLI, Copilot in Visual Studio and Cursor CLI. Visual Studio is PowerShell
# only, and Cursor's Update cuts at the frontmatter instead of the heading.
check "each install checks for this skill first" "$(count 'it already holds this skill: write nothing, and tell me to use the Update prompt' "$README")" 3
check "Cursor install checks for any OutSystems skill first" "$(count 'if it is this skill (a frontmatter block carrying `name: outsystems`), tell me to use the Update prompt' "$README")" 1
check "each install appends to an O11 file" "$(count 'it holds the O11 skill: keep it, append this skill to its end as described under Appending below' "$README")" 4
check "each append asks first when git tracks the file" "$(count 'Appending: first run `git ls-files --error-unmatch F`; if it succeeds, the file is tracked by git, so tell me the append will block `git pull` in that clone until I commit or stash the change, and ask before you append.' "$README")" 4
check "each append is checked afterwards" "$(count 'Then check that the file'"'"'s first line is unchanged and that it contains the line `# OutSystems - Remote MCP` exactly once.' "$README")" 4
check "each append and replace rules out re-encoding" "$(count 'never `>>`, `Add-Content`, `Set-Content` or `Out-File` in PowerShell, which re-encode the text' "$README")" 8
check "each Update handles an appended copy" "$(count 'keep every byte before' "$README")" 4
check "install and Update name the O11 heading" "$(count '# OutSystems 11 OML editing via the Service Studio MCP server' "$README")" 8
check "bash append command, verbatim" "$(count "\`$BASH_APPEND\`" "$README")" 3
check "PowerShell append command, verbatim" "$(count "\`$PS_APPEND\`" "$README")" 4
check "bash replace at the heading, verbatim" "$(count "\`$BASH_REPLACE_HEADING\`" "$README")" 2
check "PowerShell replace at the heading, verbatim" "$(count "\`$PS_REPLACE_HEADING\`" "$README")" 3
check "bash replace at the frontmatter, verbatim" "$(count "\`$BASH_REPLACE_FRONTMATTER\`" "$README")" 1
check "PowerShell replace at the frontmatter, verbatim" "$(count "\`$PS_REPLACE_FRONTMATTER\`" "$README")" 1
row=$(grep -F -- '| The agent works on ODC when you meant OutSystems 11 (O11)' "$README")
check "has the troubleshooting row once" "$(printf '%s\n' "$row" | grep -c .)" 1
check_match "troubleshooting row links the docs page" "$row" 'use_outsystems_mcp_in_odc_alongside_o11/\)'

finish
