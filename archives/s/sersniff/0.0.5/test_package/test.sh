#!/bin/sh
# test_package/test.sh — smoke test for the sersniff executable.
# Usage: test.sh [bindir]
# BINDIR (argv $1) is authoritative, resolved by test_package/conanfile.py
# from sersniff's package_folder. Falls back to `command -v sersniff`.
# Exercises the real built binary (no serial/TCP hardware required):
#   * `-h` prints the version banner and usage help (binary runs + version)
#   * `-b <invalid>` rejects an unsupported baud rate (option parsing)
# Emits HMBS machine-evidence markers (hard gate).
#
# OHOS readonly_tmp hardening: /tmp on the device may be read-only (erofs)
# and /bin/sh materializes $(...) in hardcoded /tmp (ignoring TMPDIR), so
# this script uses ZERO $(...) / backticks. Output capture uses plain
# redirections into $TMPDIR files + grep checks.
set -e

BINDIR="${1:-}"

# HMBS readonly_tmp: prefer the injected writable TMPDIR/TMP/TEMP.
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"sersniff 0.0.5 ships no upstream test framework: Makefile has only all/clean targets, no check/test target, no tests/ directory, no gtest/pytest bindings (audited for MANIFEST).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":3,"passedCount":0}'
    exit 1
}

# Resolve the sersniff binary.
SERSNIFF=""
if [ -n "$BINDIR" ] && [ -f "$BINDIR/sersniff" ]; then
    SERSNIFF="$BINDIR/sersniff"
    echo "[test] sersniff resolved via bindir argv: $SERSNIFF"
elif command -v sersniff >/dev/null 2>&1; then
    command -v sersniff >"$TMPDIR/sersniff_path.txt" 2>/dev/null || true
    if read -r SERSNIFF <"$TMPDIR/sersniff_path.txt" 2>/dev/null && [ -n "$SERSNIFF" ] && [ -f "$SERSNIFF" ]; then
        echo "[test] sersniff resolved via PATH: $SERSNIFF"
    else
        SERSNIFF="sersniff"
        echo "[test] sersniff resolved via PATH name: sersniff"
    fi
else
    echo "[test] sersniff binary NOT in PATH"
    if [ -n "$BINDIR" ]; then
        echo "[test] bindir listing:"
        ls -la "$BINDIR" 2>&1 || true
    fi
    echo "[test] PATH=$PATH"
    fail
fi

# Verify it is a real executable file before relying on it.
if [ ! -x "$SERSNIFF" ]; then
    echo "[test] FAIL: $SERSNIFF is not executable" >&2
    fail
fi
echo "[test] sersniff binary: $SERSNIFF"

PASS_COUNT=0

# Case 1: -h prints the version banner "sersniff v0.0.5".
echo "[test] run: $SERSNIFF -h (expect version banner)"
"$SERSNIFF" -h >"$TMPDIR/sersniff_help.txt" 2>&1 || true
cat "$TMPDIR/sersniff_help.txt" 2>/dev/null || true
if grep -q "sersniff v0\.0\.5" "$TMPDIR/sersniff_help.txt" 2>/dev/null; then
    echo "[test] PASS: version banner 'sersniff v0.0.5' present"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: version banner missing" >&2
fi

# Case 2: -h prints usage help (Usage: ...).
echo "[test] run: $SERSNIFF -h (expect usage help)"
if grep -qi "Usage:" "$TMPDIR/sersniff_help.txt" 2>/dev/null; then
    echo "[test] PASS: usage help 'Usage:' present"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: usage help missing" >&2
fi

# Case 3: -b <invalid baud> is rejected with an error message (option parsing).
echo "[test] run: $SERSNIFF -b 999 (expect unsupported baud error)"
"$SERSNIFF" -b 999 >"$TMPDIR/sersniff_baud.txt" 2>&1 || true
cat "$TMPDIR/sersniff_baud.txt" 2>/dev/null || true
if grep -qi "Unsupported Baud" "$TMPDIR/sersniff_baud.txt" 2>/dev/null; then
    echo "[test] PASS: unsupported baud rejected"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: unsupported baud not rejected" >&2
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"sersniff 0.0.5 ships no upstream test framework: Makefile has only all/clean targets, no check/test target, no tests/ directory, no gtest/pytest bindings (audited for MANIFEST).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

echo "[test] passed $PASS_COUNT/3 test cases"
if [ "$PASS_COUNT" -eq 3 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":3,"passedCount":3}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":3,"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi
