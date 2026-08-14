#!/usr/bin/env bash
set -euo pipefail

server="$1"
remote="$2"
bin_dir=$(dirname "$server")

test -x "$server"
test -x "$remote"
set -- "$bin_dir"/*
test "$#" -eq 2

server_help="$("$server" --help 2>&1)"
printf '%s\n' "$server_help" | grep -F "usage: p11-kit server"
printf '%s\n' "$server_help" | grep -F -- "--provider"
printf '%s\n' "$server_help" | grep -F -- "--timeout"

remote_help="$("$remote" --help 2>&1)"
printf '%s\n' "$remote_help" | grep -F "usage: p11-kit remote"
printf '%s\n' "$remote_help" | grep -F -- "--provider"

set +e
"$server" >/dev/null 2>&1
status=$?
set -e
test "$status" -eq 2
