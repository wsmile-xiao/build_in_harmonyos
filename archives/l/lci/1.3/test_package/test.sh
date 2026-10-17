#!/bin/bash
# test_package consumer test for lci 1.3 (justinmeza/lci LOLCODE interpreter).
# Runs the installed `lci` interpreter on real LOLCODE 1.3 programs through
# its public CLI and verifies observable output + exit codes — a real
# consumer verification (R34), not a stub.
#
# Usage: test.sh <work_dir>
set -u
WORK="${1:-$PWD}"
export PATH="$PATH:/system/bin"
# Use a private temp dir so scratch .lol files never pollute the
# test_package source directory (Conan 2 runs test_package with its own
# build_folder == source dir on this layout).
SCRATCH=$(mktemp -d "${TMPDIR:-$HOME/tmp}/lci-test.XXXXXX") || {
  echo "FAIL: cannot create scratch dir"; exit 1; }
trap 'rm -rf "$SCRATCH"' EXIT
WRITE_DIR="$SCRATCH"

echo "--- lci 1.3 consumer verification ---"
fail=0

# 1. Basic program: VISIBLE output + exit code 0
cat > "$WRITE_DIR/hello.lol" <<'EOF'
HAI 1.3
VISIBLE "hello from lci!"
KTHXBYE
EOF
out1=$(lci "$WRITE_DIR/hello.lol")
rc1=$?
[ "$rc1" = "0" ] || { echo "FAIL 1: lci hello exit=$rc1"; fail=1; }
echo "$out1" | grep -q "hello from lci!" || { echo "FAIL 1: unexpected output [$out1]"; fail=1; }
[ "$fail" = "0" ] && echo "PASS 1: hello program -> $out1"

# 2. Arithmetic + variables: observable result 13
cat > "$WRITE_DIR/arith.lol" <<'EOF'
HAI 1.3
I HAS A X ITZ 6
I HAS A Y ITZ 7
VISIBLE SUM OF X AN Y
KTHXBYE
EOF
out2=$(lci "$WRITE_DIR/arith.lol")
rc2=$?
[ "$rc2" = "0" ] || { echo "FAIL 2: lci arith exit=$rc2"; fail=1; }
echo "$out2" | grep -q "13" || { echo "FAIL 2: arith output [$out2]"; fail=1; }
[ "$fail" = "0" ] && echo "PASS 2: arithmetic -> $out2"

# 3. --help style CLI entry (public interface)
helptxt=$(lci --help 2>&1 || true)
echo "$helptxt" | grep -qi "usage" && echo "PASS 3: CLI help present" || {
  echo "WARN 3: no usage text from --help [$helptxt]"; }

if [ "$fail" = "0" ]; then
  echo "test lci 1.3: consumer checks PASS"
  exit 0
fi
echo "test lci 1.3: consumer checks FAILED"
exit 1
