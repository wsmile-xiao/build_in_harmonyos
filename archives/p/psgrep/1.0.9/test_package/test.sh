#!/usr/bin/env bash
# test_package/test.sh — smoke test for psgrep CLI
set -euo pipefail

WORK_DIR="${PWD}/psgrep-test-output"
mkdir -p "$WORK_DIR"

echo "[test] psgrep help"
set +e
HELP_OUTPUT="$(psgrep -h 2>&1)"
HELP_STATUS=$?
set -e
if [ "$HELP_STATUS" -eq 1 ] && printf '%s\n' "$HELP_OUTPUT" | grep -q "Usage:"; then
    echo "✅ psgrep -h shows usage with upstream exit status 1"
else
    echo "❌ psgrep -h unexpected status/output"
    printf '%s\n' "$HELP_OUTPUT"
    exit 1
fi

echo "[test] psgrep version"
set +e
VERSION_OUTPUT="$(psgrep -v 2>&1)"
VERSION_STATUS=$?
set -e
if [ "$VERSION_STATUS" -eq 2 ] && printf '%s\n' "$VERSION_OUTPUT" | grep -q "psgrep version 1.0.9"; then
    echo "✅ psgrep -v shows version with upstream exit status 2"
else
    echo "❌ psgrep -v unexpected status/output"
    printf '%s\n' "$VERSION_OUTPUT"
    exit 1
fi

echo "[test] psgrep simplified search"
psgrep -n -s python >"$WORK_DIR/psgrep-simplified.out" || {
    echo "❌ psgrep -n -s python failed"
    exit 1
}

echo "[test] psgrep PID-only search"
psgrep -d python >"$WORK_DIR/psgrep-pids.out" || {
    echo "❌ psgrep -d python failed"
    exit 1
}
if [ -s "$WORK_DIR/psgrep-pids.out" ] && ! awk 'NF && (NF != 1 || $1 !~ /^[0-9]+$/) {bad=1} END {exit bad}' "$WORK_DIR/psgrep-pids.out"; then
    echo "❌ psgrep -d emitted non-PID output"
    cat "$WORK_DIR/psgrep-pids.out"
    exit 1
fi

echo "[test] psgrep smoke test: PASS"
