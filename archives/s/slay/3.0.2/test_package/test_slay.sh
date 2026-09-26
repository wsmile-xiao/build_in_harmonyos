#!/bin/sh
# Intentionally pass no user name: never execute slay's process-killing branch.
set -eu
SLAY_BUTTHEAD=off
export SLAY_BUTTHEAD
slay=$1

check_usage() {
    set +e
    output=$(sh "$slay" "$@" 2>&1)
    code=$?
    set -e
    [ "$code" -eq 127 ] || { printf 'Unexpected exit %s\n' "$code"; exit 1; }
    case "$output" in
        *'usage: slay [-signal] name [name...]'*'Kills all processes belonging to any of the given names.'*) : ;;
        *) printf 'Unexpected help output: %s\n' "$output"; exit 1 ;;
    esac
}

check_usage
check_usage --help
check_usage -clean --help
printf '3/3 safe CLI argument checks passed\n'
