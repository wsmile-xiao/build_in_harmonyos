#!/bin/sh
# test_package/test.sh - smoke test for alive executable.
# Usage: test.sh [bindir]
# BINDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from alive's package_folder. Falls back to `command -v alive` / $ALIVE.
# Only offline assertions (--help/--version); never runs bare `alive` (would ping loop).
# Emits HMBS machine-evidence markers (hard gate).
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs), and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output capture uses plain redirections into $TMPDIR files + grep checks.
set -e

BINDIR="${1:-}"

# HMBS readonly_tmp: /tmp on the device is read-only (erofs). Prefer the
# injected writable TMPDIR/TMP/TEMP for any temp files (shell, guile
# runtime). The parent conanfile.py already seeds TMPDIR before exec, but
# re-resolve here in case the script is invoked directly.
# NOTE: no $(...) below on purpose (see header); use $PWD, not $(pwd).
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
if [ -z "${XDG_CACHE_HOME:-}" ]; then
    export XDG_CACHE_HOME="$TMPDIR"
fi
export GUILE_AUTO_COMPILE=0

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"alive 2.0.3 ships no upstream test framework: no test directory, no make check target, no gtest/pytest bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":2,"passedCount":0}'
    exit 1
}

echo "[test] alive binary resolution (bindir='${BINDIR:-}')"

# ALIVE_SCRIPT: path to the alive script file (run via guile -s).
# ALIVE_DIRECT: bare command name fallback (resolved via PATH at exec).
ALIVE_SCRIPT=""
ALIVE_DIRECT=""
if [ -n "$BINDIR" ] && [ -f "$BINDIR/alive" ]; then
    ALIVE_SCRIPT="$BINDIR/alive"
    echo "[test] alive resolved via bindir argv: $ALIVE_SCRIPT"
elif [ -n "${ALIVE:-}" ] && [ -f "$ALIVE" ]; then
    ALIVE_SCRIPT="$ALIVE"
    echo "[test] alive resolved via \$ALIVE fallback: $ALIVE_SCRIPT"
elif command -v alive >/dev/null 2>&1; then
    # Capture `command -v` output via a TMPDIR file + builtin `read`
    # (no command substitution: that would need a /tmp temp file).
    command -v alive >"$TMPDIR/alive_path.txt" 2>/dev/null || true
    if read -r ALIVE_DIRECT <"$TMPDIR/alive_path.txt" 2>/dev/null && [ -n "$ALIVE_DIRECT" ] && [ -f "$ALIVE_DIRECT" ]; then
        ALIVE_SCRIPT="$ALIVE_DIRECT"
        ALIVE_DIRECT=""
        echo "[test] alive resolved via PATH: $ALIVE_SCRIPT"
    else
        ALIVE_DIRECT="alive"
        echo "[test] alive resolved via PATH name: alive"
    fi
else
    echo "[test] alive binary NOT in PATH"
    if [ -n "$BINDIR" ]; then
        echo "[test] bindir listing:"
        ls -la "$BINDIR" 2>&1 || true
        echo "[test] bindir find:"
        find "$BINDIR" -maxdepth 2 -ls 2>&1 || true
    fi
    echo "[test] PATH=$PATH"
    fail
fi

HAVE_GUILE=0
if command -v guile >/dev/null 2>&1; then
    HAVE_GUILE=1
    echo "[test] guile resolved:"
    command -v guile || true
else
    echo "[test] WARN: guile NOT in PATH (alive needs it)"
    echo "[test] PATH=$PATH"
fi

if [ "$HAVE_GUILE" = "1" ]; then
    echo "[test] alive invocation: guile -s ${ALIVE_SCRIPT:-$ALIVE_DIRECT}"
else
    echo "[test] alive invocation: ${ALIVE_SCRIPT:-$ALIVE_DIRECT}"
fi

run_alive() {
    # Always prefer the guile interpreter explicitly: bin/alive's shebang
    # (#!/usr/bin/env guile -s) needs /usr/bin/env, which is absent on
    # minimal OHOS roots (direct exec then dies with 127). `guile -s
    # <script>` is exactly what that shebang would run. This also works
    # when the exec bit was lost (HMBS_CAP_CHMOD=0).
    if [ "$HAVE_GUILE" = "1" ] && [ -n "$ALIVE_SCRIPT" ] && [ -f "$ALIVE_SCRIPT" ]; then
        guile --no-auto-compile -s "$ALIVE_SCRIPT" "$@" 2>&1
    elif [ -n "$ALIVE_DIRECT" ]; then
        "$ALIVE_DIRECT" "$@" 2>&1
    elif [ -n "$ALIVE_SCRIPT" ]; then
        "$ALIVE_SCRIPT" "$@" 2>&1
    else
        echo "[test] FAIL: no alive invocation available" 2>&1
        return 127
    fi
}

PASS_COUNT=0

echo "[test] run: alive --version"
run_alive --version >"$TMPDIR/alive_version.txt" 2>&1 || true
cat "$TMPDIR/alive_version.txt" || true
if grep -q "2\.0\.3" "$TMPDIR/alive_version.txt" 2>/dev/null; then
    echo "[test] PASS: --version contains 2.0.3"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: --version missing 2.0.3" >&2
fi

echo "[test] run: alive --help"
run_alive --help >"$TMPDIR/alive_help.txt" 2>&1 || true
cat "$TMPDIR/alive_help.txt" || true
if grep -q "Usage" "$TMPDIR/alive_help.txt" 2>/dev/null; then
    echo "[test] PASS: --help contains Usage"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: --help missing Usage" >&2
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"alive 2.0.3 ships no upstream test framework: no test directory, no make check target, no gtest/pytest bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

if [ "$PASS_COUNT" -eq 2 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":2,"passedCount":2}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":2,"passedCount":0}'
    exit 1
fi
