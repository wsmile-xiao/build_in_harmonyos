#!/bin/bash
set -euo pipefail

bam="$1"
work_dir="${TMPDIR:-/tmp}/covtobed-test-$$"
mkdir -p "$work_dir"
trap 'rm -rf "$work_dir"' EXIT

covtobed --version | grep -F "covtobed 1.3.5" >/dev/null
covtobed --help 2>&1 | grep -F "Computes coverage from alignments" >/dev/null

covtobed -m 1 "$bam" >"$work_dir/actual.bed"
printf '%s\n' \
  $'NC_001416.1\t999\t1099\t20' \
  $'NC_001416.1\t1999\t2099\t5' \
  $'NC_001416.1\t2499\t2599\t5' \
  >"$work_dir/expected.bed"
diff -u "$work_dir/expected.bed" "$work_dir/actual.bed"

printf '%s\n' "HMBS_TEST_SUMMARY discovered=3 passed=3 failed=0 skipped=0"
