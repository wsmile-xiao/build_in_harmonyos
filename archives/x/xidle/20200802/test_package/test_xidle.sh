#!/bin/sh
# test_xidle.sh — consumer test for xidle 20200802
# Asserts the installed xidle binary:
#   1. exists at the expected path and is executable,
#   2. exits non-zero on `--help` (upstream usage() → exit(1)),
#   3. file(1) reports it as an ELF.
#
# HMBS evidence marker (HMBS_TEST_PACKAGE_RESULT) is emitted at the end,
# after all 3 assertions have actually executed. `passed` reflects the
# real assertion count, not the exit code alone.
# Note: no `set -eu` — the target /bin/sh (toybox ash) rejects `set -eu`
# with "set: -: unknown option", and the explicit FAILED counter below
# already gates every assertion without needing set -e early-exit.
# This file MUST use LF line endings — toybox sh parses a trailing CR as
# part of the command, which breaks backslash line continuations.

FAILED=0
XIDLE_BIN="${XIDLE_BIN:-}"

if [ -z "$XIDLE_BIN" ]; then
    for cand in "${XIDLE_ROOT:-}/bin/xidle" "$(dirname "$0")/xidle" "./xidle"; do
        if [ -x "$cand" ]; then
            XIDLE_BIN="$cand"
            break
        fi
    done
fi

# Assertion 1: binary exists and is executable
if [ -z "$XIDLE_BIN" ] || [ ! -x "$XIDLE_BIN" ]; then
    echo "FAIL: xidle binary not found or not executable (XIDLE_BIN=${XIDLE_BIN})"
    FAILED=$((FAILED + 1))
else
    echo "PASS: xidle binary found at ${XIDLE_BIN}"
fi

# Assertion 2: xidle --help exits non-zero (usage() → exit(1))
if [ -n "$XIDLE_BIN" ] && [ -x "$XIDLE_BIN" ]; then
    if "$XIDLE_BIN" --help >/dev/null 2>&1; then
        echo "FAIL: xidle --help exited 0, expected non-zero"
        FAILED=$((FAILED + 1))
    else
        echo "PASS: xidle --help exits non-zero"
    fi
else
    FAILED=$((FAILED + 1))
fi

# Assertion 3: file(1) reports an ELF
if [ -n "$XIDLE_BIN" ] && [ -x "$XIDLE_BIN" ]; then
    FILE_OUT="$(file "$XIDLE_BIN")"
    case "$FILE_OUT" in
        *ELF*) echo "PASS: file reports ELF";;
        *) echo "FAIL: file does not report ELF: ${FILE_OUT}"; FAILED=$((FAILED + 1));;
    esac
else
    FAILED=$((FAILED + 1))
fi

# HMBS machine-evidence marker — emitted after the real assertions ran.
# 3 assertions total; passed = 3 - FAILED.
if [ "$FAILED" -eq 0 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test_xidle.sh <xidle_bin>"}'
    echo "test_xidle: OK"
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test_xidle.sh <xidle_bin>"}'
    exit 1
fi
