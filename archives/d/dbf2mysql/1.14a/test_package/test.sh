#!/data/service/hnp/bin/bash
set -euo pipefail

dbf2mysql_bin="$1"
mysql2dbf_bin="$2"
assertions=0

pass() {
    assertions=$((assertions + 1))
    printf '[pass] %s\n' "$1"
}

fail() {
    printf '[fail] %s\n' "$1" >&2
    exit 1
}

[ -x "$dbf2mysql_bin" ] && pass "dbf2mysql is executable" || fail "dbf2mysql is not executable"
[ -x "$mysql2dbf_bin" ] && pass "mysql2dbf is executable" || fail "mysql2dbf is not executable"

set +e
dbf_usage="$($dbf2mysql_bin 2>&1)"
dbf_rc=$?
set -e
[ "$dbf_rc" -eq 1 ] && pass "dbf2mysql usage exit status" || fail "unexpected dbf2mysql usage exit status"
case "$dbf_usage" in *"dbf2mysql 1.14a"*) pass "dbf2mysql version output" ;; *) fail "missing dbf2mysql version" ;; esac
case "$dbf_usage" in *"usage: dbf2mysql"*) pass "dbf2mysql usage output" ;; *) fail "missing dbf2mysql usage" ;; esac

set +e
mysql_usage="$($mysql2dbf_bin 2>&1)"
mysql_rc=$?
set -e
[ "$mysql_rc" -eq 1 ] && pass "mysql2dbf usage exit status" || fail "unexpected mysql2dbf usage exit status"
case "$mysql_usage" in *"mysql2dbf 1.14a"*) pass "mysql2dbf version output" ;; *) fail "missing mysql2dbf version" ;; esac
case "$mysql_usage" in *"usage:"*"mysql2dbf"*) pass "mysql2dbf usage output" ;; *) fail "missing mysql2dbf usage" ;; esac

task_tmp="${TMPDIR:-.}/dbf2mysql-consumer-$$"
mkdir -p "$task_tmp"
trap 'rm -rf "$task_tmp"' EXIT

set +e
missing_input="$($dbf2mysql_bin "$task_tmp/missing.dbf" 2>&1)"
missing_input_rc=$?
set -e
[ "$missing_input_rc" -eq 1 ] && pass "missing DBF input exit status" || fail "unexpected missing DBF exit status"
case "$missing_input" in *"Couldn't open xbase-file "*"missing.dbf"*) pass "missing DBF input diagnostic" ;; *) fail "missing DBF diagnostic absent" ;; esac

set +e
bad_output="$($mysql2dbf_bin -d test -t test "$task_tmp/missing/output.dbf" 2>&1)"
bad_output_rc=$?
set -e
[ "$bad_output_rc" -eq 1 ] && pass "invalid DBF output exit status" || fail "unexpected invalid output exit status"
case "$bad_output" in *"Couldn't open xbase-file for writing"*) pass "invalid DBF output diagnostic" ;; *) fail "invalid output diagnostic absent" ;; esac

printf '[result] assertions passed: %s\n' "$assertions"
[ "$assertions" -eq 12 ] || fail "assertion count mismatch"
