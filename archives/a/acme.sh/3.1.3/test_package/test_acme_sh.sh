#!/bin/bash
# Verify the packaged acme.sh wrapper and helper directories.

set -euo pipefail

ACME_BIN="${1:-}"
TEST_SHELL="${2:-}"

if [ -z "$ACME_BIN" ] || [ -z "$TEST_SHELL" ]; then
    echo "ERROR: acme.sh binary path and shell path are required"
    exit 1
fi

if [ ! -x "$ACME_BIN" ]; then
    echo "ERROR: $ACME_BIN not found or not executable"
    exit 1
fi

if [ ! -x "$TEST_SHELL" ]; then
    echo "ERROR: $TEST_SHELL not found or not executable"
    exit 1
fi

pkg_root="$(CDPATH= cd -- "$(dirname -- "$ACME_BIN")/.." && pwd)"
for dirname in dnsapi deploy notify; do
    if [ ! -d "$pkg_root/libexec/acme.sh/$dirname" ]; then
        echo "ERROR: missing helper directory $dirname"
        exit 1
    fi
done

output="$("$TEST_SHELL" "$ACME_BIN" --version)"
printf "%s\n" "$output" | grep -F "https://github.com/acmesh-official/acme.sh"
printf "%s\n" "$output" | grep -F "v3.1.3"

path_output="$(cd "$pkg_root" && PATH="$pkg_root/bin:$PATH" "$TEST_SHELL" -c 'acme.sh --version')"
printf "%s\n" "$path_output" | grep -F "v3.1.3"

help_output="$("$TEST_SHELL" "$ACME_BIN" --help)"
printf "%s\n" "$help_output" | grep -F "Usage:"
printf "%s\n" "$help_output" | grep -F -- "--issue"

echo "PASS: acme.sh wrapper, PATH lookup, helper directories, version output, and help output are valid"
