#!/usr/bin/env bash
# test_ndenv.sh — smoke test for ndenv 0.4.0.
# R34: executes the packaged artifact (no print-only stubs).
# Usage: test_ndenv.sh <package bin dir>
# 6 assertions: presence/executable, bash shebang, bash -n over libexec,
# --version output, `commands` dispatcher listing, `versions` on empty root.
set -uo pipefail

BIN_DIR="${1:?usage: test_ndenv.sh <package bin dir>}"

# 0. HMBS/HarmonyOS hardening (must run before any $(...) subshell):
# conan test() cwd may already be deleted on the device, so every bash
# child prints "shell-init: getcwd: cannot access parent directories" and
# the ndenv dispatcher (set -e plus cwd="$(pwd)" / NDENV_DIR="$(pwd)")
# aborts with empty output. Sanitize cwd first so children inherit a
# valid directory.
if [ -d "$BIN_DIR" ]; then
    cd "$BIN_DIR" 2>/dev/null || cd / 2>/dev/null || true
else
    cd / 2>/dev/null || true
fi
# Dispatcher uses $NDENV_DIR as cwd override when set; make sure a stale
# exported value cannot point at a deleted directory.
unset NDENV_DIR || true

FAIL=0
PASS=0
NODENV="$BIN_DIR/ndenv"
LIBEXEC_DIR="$BIN_DIR/../libexec"

pass() {
    PASS=$((PASS + 1))
    echo "[ok] $1"
}

fail() {
    FAIL=1
    echo "[fail] $1"
}

# 1. bin/ndenv exists and is executable
if [ -x "$NODENV" ]; then
    pass "bin/ndenv exists and is executable"
else
    fail "bin/ndenv missing or not executable in $BIN_DIR"
fi

# 2. shebang declares bash (follow the bin -> libexec symlink)
if [ -f "$NODENV" ]; then
    SHEBANG=$(head -n 1 "$NODENV")
    case "$SHEBANG" in
        *bash*) pass "shebang declares bash: $SHEBANG" ;;
        *) fail "unexpected shebang: $SHEBANG" ;;
    esac
else
    fail "bin/ndenv is not a file, cannot check shebang"
fi

# 3. bash syntax check over every libexec script
if [ -d "$LIBEXEC_DIR" ]; then
    SYNTAX_FAIL=0
    for script in "$LIBEXEC_DIR"/ndenv "$LIBEXEC_DIR"/ndenv-*; do
        [ -f "$script" ] || continue
        if ! bash -n "$script"; then
            echo "[fail] bash -n failed: $script"
            SYNTAX_FAIL=1
        fi
    done
    if [ "$SYNTAX_FAIL" -eq 0 ]; then
        pass "bash -n syntax check passed for libexec scripts"
    else
        fail "bash -n syntax check failed for libexec scripts"
    fi
else
    fail "libexec dir missing: $LIBEXEC_DIR"
fi

# Functional checks need the dispatcher on PATH plus an isolated root.
# Resolve libexec without depending on `pwd` (broken cwd makes pwd fail).
if command -v readlink >/dev/null 2>&1; then
    REAL_LIBEXEC=$(readlink -f "$LIBEXEC_DIR" 2>/dev/null || echo "$LIBEXEC_DIR")
else
    REAL_LIBEXEC="$LIBEXEC_DIR"
fi
# /tmp can be read-only on the device; prefer HMBS-injected writable
# TMPDIR/TMP/TEMP, fall back to HOME, then /tmp. Pick first creatable dir.
NDENV_ROOT=""
for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${HOME:-}" "/tmp"; do
    [ -n "$_cand" ] || continue
    _cand="$_cand/ndenv-test-root"
    if mkdir -p "$_cand" 2>/dev/null && [ -d "$_cand" ] && [ -w "$_cand" ]; then
        NDENV_ROOT="$_cand"
        break
    fi
done
if [ -z "$NDENV_ROOT" ]; then
    fail "no writable directory for isolated NDENV_ROOT"
    NDENV_ROOT="${TMPDIR:-/tmp}/ndenv-test-root"
fi
export NDENV_ROOT
export PATH="$REAL_LIBEXEC:$BIN_DIR:$PATH"

# 4. ndenv --version reports 0.4.0 (merge stderr so dispatch errors are visible)
VERSION_OUT=$("$NODENV" --version 2>&1 || true)
case "$VERSION_OUT" in
    *0.4.0*) pass "ndenv --version reports 0.4.0: $VERSION_OUT" ;;
    *) fail "ndenv --version unexpected output: $VERSION_OUT" ;;
esac

# 5. ndenv commands dispatcher lists subcommands (exercises PATH dispatch)
COMMANDS_OUT=$("$NODENV" commands 2>&1 || true)
case "$COMMANDS_OUT" in
    *versions*) pass "ndenv commands lists subcommands" ;;
    *) fail "ndenv commands output missing subcommands: $COMMANDS_OUT" ;;
esac

# 6. ndenv versions exits 0 against an empty root
if "$NODENV" versions >/dev/null 2>&1; then
    pass "ndenv versions exits 0 on empty NDENV_ROOT"
else
    fail "ndenv versions exited non-zero on empty NDENV_ROOT"
fi

echo "[info] ndenv smoke test: $PASS passed, failures=$FAIL"
exit "$FAIL"
