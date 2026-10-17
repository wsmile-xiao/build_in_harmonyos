#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for marst (Algol-to-C translator)
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binaries and runtime library.
set -eu

# Locate the package root from the installed binary (conanrun PATH)
MARST_BIN=$(command -v marst)
PKGDIR=$(cd "$(dirname "$MARST_BIN")/.." && pwd)
INC="-I$PKGDIR/include"
LIB="$PKGDIR/lib/libalgol.a"
echo "[test] package root: $PKGDIR"

echo "[test] marst --version"
marst --version 2>&1 | grep -q "Version 2.8"
echo "OK: --version reports Version 2.8"

echo "[test] marst --help"
marst --help | grep -q "Usage:"
echo "OK: --help prints usage"

echo "[test] translate Algol -> C (same suffix rule as upstream Makefile)"
cat > hello.alg <<'EOF'
begin
  outstring(1, "Hello, world!\n")
end
EOF
marst -t -w hello.alg -o hello.c
grep -q "Hello" hello.c
echo "OK: translator produced C code ($(wc -l < hello.c) lines)"

echo "[test] compile translated C against libalgol and run it (upstream check methodology)"
CC_BIN=clang
command -v clang >/dev/null 2>&1 || CC_BIN=cc
"$CC_BIN" $INC hello.c -o hello "$LIB" -lm
OUT=$(./hello)
echo "$OUT"
echo "$OUT" | grep -q "Hello, world!"
echo "OK: translated program ran and printed Hello, world!"

echo "ALL CONSUMER TESTS PASSED"
