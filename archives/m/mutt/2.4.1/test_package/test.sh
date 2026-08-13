#!/bin/bash
# test.sh — mutt 2.4.1 test_package functional test
# R34: Must actually execute the mutt binary, not just print strings.
set -euo pipefail

# Verify mutt binary is available
command -v mutt >/dev/null

# Test 1: Version output (mutt -v)
if ! output="$(mutt -v 2>&1)"; then
    printf '%s\n' 'ERROR: mutt -v execution failed' >&2
    exit 1
fi
test -n "$output"
# Verify version string is present
if ! printf '%s\n' "$output" | grep -Eiq 'Mutt 2\.4\.1'; then
    printf '%s\n' 'FAIL: mutt -v output missing version string "Mutt 2.4.1"' >&2
    exit 1
fi
# Verify system detection
if ! printf '%s\n' "$output" | grep -Eiq 'HarmonyOS|aarch64'; then
    printf '%s\n' 'FAIL: mutt -v output missing system detection (HarmonyOS/aarch64)' >&2
    exit 1
fi
# Verify SSL support compiled in
if ! printf '%s\n' "$output" | grep -Eiq 'USE_SSL_OPENSSL'; then
    printf '%s\n' 'FAIL: mutt -v output missing USE_SSL_OPENSSL' >&2
    exit 1
fi
# Verify IMAP/POP/SMTP support
if ! printf '%s\n' "$output" | grep -Eiq 'USE_POP|USE_IMAP|USE_SMTP'; then
    printf '%s\n' 'FAIL: mutt -v output missing IMAP/POP/SMTP support' >&2
    exit 1
fi

# Test 2: Help output (mutt -h)
if ! help_output="$(mutt -h 2>&1)"; then
    printf '%s\n' 'ERROR: mutt -h execution failed' >&2
    exit 1
fi
test -n "$help_output"
if ! printf '%s\n' "$help_output" | grep -Eiq 'usage|options'; then
    printf '%s\n' 'FAIL: mutt -h output missing usage/options' >&2
    exit 1
fi

printf '%s\n' "$output"
