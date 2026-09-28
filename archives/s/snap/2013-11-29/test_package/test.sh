#!/bin/sh
# test_package consumer test for SNAP 2013-11-29.
# Exercises the installed binaries end to end: CLI contract (--version/-help/
# --help, all rc=0) and a real gene-prediction run with the packaged stock HMM
# on an embedded deterministic A. thaliana 1500bp sample, asserting the exact
# GFF output line. The prediction line was verified byte-stable across repeated
# runs on the build host (clang 15, -O2 -fcommon).
export PATH="$PATH:/system/bin"

DIR="$(cd "$(dirname "$0")" && pwd)"
HMM="${SNAP_RES:-$DIR/../../res}/HMM/minimal.hmm"
pass=0
fail=0

check_rc() { # name rc expected
  if [ "$2" = "$3" ]; then
    pass=$((pass+1)); echo "PASS: $1 (rc=$2)"
  else
    fail=$((fail+1)); echo "FAIL: $1 rc=$2 want $3"
  fi
}

# 1. --version: rc=0 and exact banner (added by patches/0001-cli-help-version.patch)
out="$(snap --version 2>/dev/null)"; rc=$?
check_rc "snap --version" "$rc" "0"
if [ "$out" = "snap 2013-11-29" ]; then
  pass=$((pass+1)); echo "PASS: --version output [${out}]"
else
  fail=$((fail+1)); echo "FAIL: --version output [${out}]"
fi

# 2. -help: rc=0, contains the program self-description
help_out="$(snap -help 2>/dev/null)"; rc=$?
check_rc "snap -help" "$rc" "0"
echo "$help_out" | grep -q "The general form of the snap command line is" && {
  pass=$((pass+1)); echo "PASS: -help self-description"
} || {
  fail=$((fail+1)); echo "FAIL: -help missing self-description"
}

# 3. --help: rc=0 and byte-identical to -help
dd_out="$(snap --help 2>/dev/null)"; rc=$?
check_rc "snap --help" "$rc" "0"
if [ "$dd_out" = "$help_out" ]; then
  pass=$((pass+1)); echo "PASS: --help identical to -help"
else
  fail=$((fail+1)); echo "FAIL: --help differs from -help"
fi

# 4. real gene prediction: stock minimal.hmm on embedded deterministic fasta
[ -f "$HMM" ] || { echo "FAIL: HMM not found at $HMM"; exit 1; }
pred="$(snap "$HMM" "$DIR/sample.fa" -gff 2>/dev/null)"; rc=$?
check_rc "snap gene prediction" "$rc" "0"
expected="$(printf 'sample\tSNAP\tEinit\t1010\t1387\t10.597\t+\t.\tsample-snap.1')"
if [ "$pred" = "$expected" ]; then
  pass=$((pass+1)); echo "PASS: prediction GFF line verbatim [${pred}]"
else
  fail=$((fail+1)); echo "FAIL: prediction [${pred}] want [${expected}]"
fi

# 5. hmm-info reads back the packaged HMM
hmm_info="$(hmm-info "$HMM" 2>/dev/null)"; rc=$?
check_rc "hmm-info minimal.hmm" "$rc" "0"

total=$((pass+fail))
echo "test snap 2013-11-29: ${pass}/${total} checks PASS, ${fail} FAIL"
[ "$fail" = "0" ] || exit 1
exit 0
