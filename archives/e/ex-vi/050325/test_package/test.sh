#!/usr/bin/env bash
# test_package/test.sh — functional smoke test for the ex-vi ex binary (R34).
#
# Drives the installed `ex` line editor end-to-end: writes a small input
# file, runs ex to print the buffer and quit, and asserts that ex echoed
# the file content back (proving it parsed the file, created its temp
# buffer, and executed the `p`/`q` commands). Run via the conanrun env so
# that the package's bin/ is on PATH (ex, vi, view, ...).
set -euo pipefail

WORKDIR="$(mktemp -d "${TMPDIR:-/data/service/hnp/tmp}/exvi-test.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

# ex defaults its temp directory to /var/tmp (ex_data.c: direct[]). That
# path does not exist on OHOS, so ex aborts with 'No such file or directory'
# before editing. Override it via EXINIT 'set directory=...'. NOTE: ex only
# honours EXINIT when NOT run with -s (the -s "fast" flag skips EXINIT
# processing — see ex.c ~line 579-588), so we do NOT pass -s.
INPUT="$WORKDIR/input.txt"
printf 'hello ex-vi smoke test\nsecond line\n' > "$INPUT"

# 1. --version smoke (ex-vi 050325 recognises GNU --version via patch 0003).
ex --version > /dev/null 2>&1 || { echo "FAIL: ex --version did not exit 0"; exit 1; }
echo "   ex --version: OK"

# 2. Functional run: print the whole buffer then quit.
OUT="$(printf '1,$p\nq\n' | \
    EXINIT="set directory=$WORKDIR" \
    TERM=dumb \
    TMPDIR="$WORKDIR" \
    ex "$INPUT" 2>/dev/null)"
RC=$?

echo "   ex exit code: $RC"
echo "   ex output: <<$OUT>>"

# ex should have printed the file content back (it echoes the buffer for p).
if printf '%s\n' "$OUT" | grep -q "hello ex-vi smoke test"; then
    echo "OK: ex read the file and printed the buffer content"
    exit 0
fi

echo "FAIL: ex did not print the expected buffer content"
exit 1
