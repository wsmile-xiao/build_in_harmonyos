#!/bin/sh
# test_gate.sh — validate the packaged abGate LV2 bundle.
# Usage: test_gate.sh <path-to-abGate.lv2-bundle>
#
# Real assertions only: every check fails (non-zero exit) when the
# condition is not met — no hardcoded paths, no unconditional pass.
# R25: shell scripts must start with `set -euo pipefail`.
set -euo pipefail

BUNDLE="$1"
fail=0

check_file() { # name path
    if [ -f "$2" ]; then
        echo "ok   : $1 exists ($(wc -c < "$2") bytes)"
    else
        echo "FAIL : $1 missing at $2"
        fail=$((fail + 1))
    fi
}

if [ ! -d "$BUNDLE" ]; then
    echo "FAIL : LV2 bundle directory not found: $BUNDLE"
    exit 1
fi
echo "ok   : bundle directory $BUNDLE"

check_file "manifest.ttl" "$BUNDLE/manifest.ttl"
check_file "gate.ttl" "$BUNDLE/gate.ttl"
check_file "gate.so" "$BUNDLE/gate.so"

# gate.so must be an ELF binary — verify the magic bytes directly so the
# check does not depend on the external `file` command.
GATE_SO="$BUNDLE/gate.so"
if [ -f "$GATE_SO" ]; then
    magic="$(head -c 4 "$GATE_SO" | od -An -tx1 | tr -d ' \n')"
    if [ "$magic" = "7f454c46" ]; then
        echo "ok   : gate.so is ELF (magic verified)"
    else
        echo "FAIL : gate.so is not an ELF binary (magic=$magic)"
        fail=$((fail + 1))
    fi
fi

if [ "$fail" -ne 0 ]; then
    echo "abgate test: $fail check(s) failed"
    exit 1
fi
echo "abgate test: all checks passed"
exit 0
