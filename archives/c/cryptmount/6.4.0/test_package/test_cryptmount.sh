#!/bin/sh
set -eu
exe="$1"
help_output=$("$exe" --help 2>&1)
printf '%s\n' "$help_output" | grep -F -- '--key-managers' >/dev/null
echo 'HarmonyOS PC test 1/2: native CLI help exits successfully'

set +e
version_output=$("$exe" --version 2>&1)
version_status=$?
set -e
if [ "$version_status" -ne 101 ]; then
    printf '%s\n' "$version_output" >&2
    echo "expected fail-closed config status 101, got $version_status" >&2
    exit 1
fi
printf '%s\n' "$version_output" | grep -F 'Cannot open "/etc/cryptmount/cmtab"' >/dev/null
printf '%s\n' "$version_output" | grep -F 'Security failure' >/dev/null
echo 'HarmonyOS PC test 2/2: native loader reaches the expected protected-config security gate'
