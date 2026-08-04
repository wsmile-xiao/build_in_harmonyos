#!/bin/sh
# test_package/src/test_bbrew.sh
#
# L1/L2 smoke test for the bbrew application package (shell wrapper).
#
# The Go test harness (test_bbrew_test.go) exercises the actual installed
# bbrew binary via `bbrew --version`. This shell wrapper performs the same
# invocation so the CI L0c gate (which scans .c/.cpp/.cc/.cxx/.sh/.py)
# detects a test source file, and so a non-Go CI runner can still run
# the smoke test.
#
# Usage:
#   BBREW_BIN=/path/to/brew sh test_brew.sh
#   sh test_brew.sh          # looks up bbrew on PATH
#
# Exit codes:
#   0 — bbrew --version printed a string containing the expected version
#   1 — bbrew not found, version mismatch, or placeholder binary detected
#   2 — bbrew --version exited non-zero
set -eu

BBREW_BIN="${BBREW_BIN:-}"
if [ -z "$BBREW_BIN" ]; then
    if command -v bbrew >/dev/null 2>&1; then
        BBREW_BIN="$(command -v bbrew)"
    else
        echo "FAIL: bbrew binary not found (set BBREW_BIN or add bbrew to PATH)" >&2
        exit 1
    fi
fi

EXPECTED_VERSION="2.3.2"
out="$("$BBREW_BIN" --version 2>&1)" || rc=$?
rc="${rc:-0}"

if [ "$rc" -ne 0 ]; then
    echo "FAIL: bbrew --version exited with $rc" >&2
    echo "output: $out" >&2
    exit 2
fi

case "$out" in
    *"[PLACEHOLDER]"*)
        # R9: conanfile.py builds a C placeholder when the Go toolchain is
        # unavailable; a placeholder must never pass as a genuine build.
        echo "FAIL: bbrew --version output contains placeholder marker (R9: 禁止伪造通过)" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac

case "$out" in
    *"$EXPECTED_VERSION"*)
        echo "PASS: bbrew --version output contains $EXPECTED_VERSION"
        exit 0
        ;;
    *)
        echo "FAIL: bbrew --version output does not contain $EXPECTED_VERSION" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac
