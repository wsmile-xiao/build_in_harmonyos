#!/data/service/hnp/bin/bash
set -euo pipefail

run_command() {
  local expected_rc=$1
  local expected_pattern=$2
  shift 2
  local out
  local rc

  set +e
  out=$("$@" </dev/null 2>&1)
  rc=$?
  set -e
  test "$rc" -eq "$expected_rc"
  printf '%s\n' "$out" | grep -qiE "$expected_pattern"
}

run_command 1 'database|directory|usage|parameter' tace
run_command 1 'aql|usage|query' taql -h
run_command 1 'usage' acediff
run_command 255 'usage' acediffsorted
run_command 0 'Run the program' makeUserPasswd
run_command 1 'Usage: tagcount' tagcount

# md5test is the upstream aggregate target; package() requires both drivers it creates.
test -x "$(command -v mddriver)"
test -x "$(command -v digtest)"

set +e
out=$(mddriver </dev/null 2>&1)
rc=$?
set -e
test "$rc" -eq 0
printf '%s\n' "$out" | grep -q 'd41d8cd98f00b204e9800998ecf8427e'

set +e
out=$(digtest </dev/null 2>&1)
rc=$?
set -e
test "$rc" -eq 0
printf '%s\n' "$out" | grep -q 'Response'

echo 'ALL ACEDB TESTS PASSED'
