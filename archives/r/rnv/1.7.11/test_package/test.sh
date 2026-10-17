#!/bin/sh
# test_package/test.sh — functional test for rnv 1.7.11 executables.
# Runs in conanrun env (PATH includes the installed bin/ via VirtualRunEnv).
# POSIX-sh compatible: invoked as `sh test.sh` on the OHOS preflight
# worker where hnp/bash is not executable (Error 127 precedent).
set -eu

# HMFS/HMDFS: /tmp may be a read-only mount and the conan build-tree cwd
# may be inaccessible; move to the injected writable scratch dir and never
# write to /tmp (adcli 0.9.2 precedent). Nested :- defaults are avoided
# for maximal mksh/POSIX portability.
SCRATCH="${TMPDIR:-}"
if [ -z "$SCRATCH" ]; then SCRATCH="${TMP:-}"; fi
if [ -z "$SCRATCH" ]; then SCRATCH="${TEMP:-}"; fi
if [ -z "$SCRATCH" ]; then SCRATCH="$HOME/tmp"; fi
mkdir -p "$SCRATCH"
cd "$SCRATCH"

RNV_BIN="${RNV_BIN:-rnv}"

# Fixtures: a minimal Relax NG Compact Syntax grammar plus one valid and
# one invalid document (generated at runtime, no network needed).
cat > grammar.rnc <<'EOF'
start = element greeting { text }
EOF
cat > valid.xml <<'EOF'
<greeting>Hello</greeting>
EOF
cat > invalid.xml <<'EOF'
<farewell>Bye</farewell>
EOF

echo "[test 1/4] $RNV_BIN -v (version output)"
# NOTE: bare `rnv -v` exits 1 by design (xcl.c: no schema arg -> usage +
# return 1), so only the output text is asserted here, not the exit code.
set +e
VER_OUT="$("$RNV_BIN" -v 2>&1)"
set -e
echo "$VER_OUT" | grep -q "rnv version 1.7.11" || {
    echo "FAIL: rnv -v output missing 'rnv version 1.7.11'"
    echo "--- output ---"
    echo "$VER_OUT"
    exit 1
}

echo "[test 2/4] $RNV_BIN -c grammar.rnc (grammar check)"
"$RNV_BIN" -c grammar.rnc || {
    echo "FAIL: rnv -c rejected a valid grammar"
    exit 1
}

echo "[test 3/4] $RNV_BIN grammar.rnc valid.xml (positive validation)"
"$RNV_BIN" grammar.rnc valid.xml || {
    echo "FAIL: rnv rejected a valid document"
    exit 1
}

echo "[test 4/4] $RNV_BIN grammar.rnc invalid.xml (negative validation)"
# Falsification control: the harness must catch a real validation
# failure (exit != 0). If this ever exits 0, the tests are vacuous.
set +e
"$RNV_BIN" grammar.rnc invalid.xml >/dev/null 2>&1
RC=$?
set -e
if [ "$RC" -eq 0 ]; then
    echo "FAIL: rnv accepted an invalid document (harness is vacuous)"
    exit 1
fi

echo "[test] all rnv executable checks PASSED (4/4)"
exit 0
