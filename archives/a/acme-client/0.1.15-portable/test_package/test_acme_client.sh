#!/usr/bin/env sh
set -eu

ACME_CLIENT_BIN="$1"

if [ ! -x "$ACME_CLIENT_BIN" ]; then
    echo "ERROR: acme-client binary is missing"
    exit 1
fi

set +e
output=$("$ACME_CLIENT_BIN" 2>&1)
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "ERROR: acme-client without domains should fail with usage"
    printf "%s\n" "$output"
    exit 1
fi

if ! printf "%s\n" "$output" | grep -q "usage:"; then
    echo "ERROR: usage output is missing"
    printf "%s\n" "$output"
    exit 1
fi

if ! printf "%s\n" "$output" | grep -q "acme-client"; then
    echo "ERROR: usage output does not mention acme-client"
    printf "%s\n" "$output"
    exit 1
fi

echo "PASS: acme-client binary reports usage without network access"
