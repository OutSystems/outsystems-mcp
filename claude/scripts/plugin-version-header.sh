#!/bin/sh
# headersHelper of .mcp.json: prints the plugin version header from the
# top-level "version" of plugin.json, in plain shell for the plugin validator.
# One pass in linear time: each line splits on quotes into the text outside
# and inside JSON strings, so a brace or a "version" inside a string does
# not count.

LC_ALL=C
export LC_ALL
set -f

manifest="$(dirname "$0")/../.claude-plugin/plugin.json"
[ -r "$manifest" ] || exit 1

# Each split puts IFS back to the default at once: with a bracket in IFS,
# bash 3.2 matches a case pattern wrong.

# Sets n to the number of times the character occurs in the text.
count() { # character, text
  IFS=$1
  set -- ${2}x
  unset IFS
  n=$(($# - 1))
}

# Sets odd to 1 if the text ends in an odd number of backslashes, so the
# quote after it is escaped.
odd_backslashes() { # text
  odd=0
  case $1 in *\\) ;; *) return ;; esac
  IFS='\'
  set -- ${1}x
  unset IFS
  run=0
  for piece do
    odd=$((run % 2))
    if [ -n "$piece" ]; then run=1; else run=$((run + 1)); fi
  done
}

# Text outside strings. After the top-level "version" key, the text must be
# a colon and then the start of a string, with only whitespace around them.
outside() { # text
  rest=${1#"${1%%[![:space:]]*}"}
  case $pending in
    key)
      case $rest in
        "") ;;
        :*)
          rest=${rest#:}
          rest=${rest#"${rest%%[![:space:]]*}"}
          [ -z "$rest" ] || exit 1
          pending=value
          ;;
        *) pending= ;;
      esac
      ;;
    value) [ -z "$rest" ] || exit 1 ;;
  esac
  case $1 in
    *[][{}]*)
      count '{' "$1"; depth=$((depth + n))
      count '}' "$1"; depth=$((depth - n))
      count '[' "$1"; list=$((list + n))
      count ']' "$1"; list=$((list - n))
      ;;
  esac
}

# The part of a string up to a quote. An escaped quote continues the string;
# a string with one is never the key or a valid value.
inside() { # text
  odd_backslashes "$1"
  if [ "$odd" = 1 ]; then
    escaped=1
    return
  fi
  in=
  if [ "$pending" = value ]; then
    [ -z "$escaped" ] || exit 1
    version=$1
    pending=
  elif [ -z "$escaped" ] && [ "$1" = version ] && [ "$depth" = 1 ] && [ "$list" = 0 ]; then
    pending=key
  else
    pending=
  fi
  escaped=
}

depth=0 list=0 in='' escaped='' pending='' version=''
while IFS= read -r line || [ -n "$line" ]; do
  # Every part but the last ends at a quote. The space keeps the last part.
  first=1
  IFS='"'
  for part in $line" "; do
    unset IFS
    if [ -z "$first" ]; then
      if [ -n "$in" ]; then inside "$prev"; else outside "$prev"; in=1; fi
    fi
    first=
    prev=$part
  done
  # JSON has no line break inside a string.
  [ -z "$in" ] || exit 1
  outside "$prev"
done < "$manifest"

case $version in
  "" | *[!0-9A-Za-z.+-]*) exit 1 ;;
esac
printf '{"X-OutSystems-Plugin-Version":"%s"}\n' "$version"
