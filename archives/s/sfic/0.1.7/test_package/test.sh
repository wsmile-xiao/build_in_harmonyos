#!/data/service/hnp/bin/bash
# test_package/test.sh — sfic consumer test (7 assertions)
#
# Simulates a business component using the installed sfic CLI:
#   1. probe the binary (--version)
#   2. probe the help text
#   3. build a tdb metadata database over a file tree (-a -R)
#   4. list the database and verify every path was recorded (-l)
#   5. rebuild a second database and compare (-n/-o, expect no changes)
#   6. modify the tree, rebuild and re-compare (expect change detection)
#   7. verify the databases are distinct tdb files on disk
#
# Two independent db files are always used (sfic/tdb has a known quirk
# opening the same db file twice in one process).
set -u

T=$(cd "$(dirname "$0")" && pwd)
W="$T/.sfic-work"
rm -rf "$W"
mkdir -p "$W/app/sub" "$W/other"
printf 'alpha\n' > "$W/app/a.txt"
printf 'beta\n'  > "$W/app/sub/b.txt"
printf 'gamma\n' > "$W/other/c.txt"
DB1="$W/db1.tdb"
DB2="$W/db2.tdb"
DB3="$W/db3.tdb"

fail=0
check() { # $1 = description, $2 = 0/1 (1 = pass)
    if [ "$2" -eq 1 ]; then
        echo "[PASS] $1"
    else
        echo "[FAIL] $1"
        fail=1
    fi
}

# 1. version probe (CI L2 smoke gate uses the same entry point)
ver_out=$(sfic --version 2>&1)
ver_rc=$?
check "sfic --version exits 0 (got: $ver_out)" $([ $ver_rc -eq 0 ] && echo 1 || echo 0)

# 2. help text
sfic -h 2>&1 | grep -q "simple file integrity checker"
check "sfic -h mentions 'simple file integrity checker'" $([ $? -eq 0 ] && echo 1 || echo 0)

# 3. build a database over the tree (recursive add)
sfic -a "$DB1" -R "$W/app"
check "sfic -a DB1 -R app/ (create tdb database)" $([ $? -eq 0 ] && echo 1 || echo 0)

# 4. list: every path must be present
ok=1
list_out=$(sfic -l "$DB1") && echo "$list_out" | grep -q "$W/app/a.txt" && \
    echo "$list_out" | grep -q "$W/app/sub/b.txt" || ok=0
check "sfic -l DB1 lists all recorded paths" $ok

# 5. rebuild an identical database and compare (no changes expected)
sfic -a "$DB2" -R "$W/app"
rc_add2=$?
sfic -n "$DB2" -o "$DB1" >/dev/null 2>&1
rc_cmp_same=$?
check "no-change compare: -a DB2 + -n DB2 -o DB1 exit 0" $([ $rc_add2 -eq 0 ] && [ $rc_cmp_same -eq 0 ] && echo 1 || echo 0)

# 6. change detection: modify the tree, rebuild, compare against DB1
printf 'CHANGED\n' > "$W/app/a.txt"
sfic -a "$DB3" -R "$W/app"
rc_add3=$?
sfic -n "$DB3" -o "$DB1" > "$W/changed.txt" 2>&1
rc_cmp_changed=$?
ok=1
[ $rc_add3 -eq 0 ] || ok=0
[ $rc_cmp_changed -ne 0 ] || ok=0
grep -q "$W/app/a.txt" "$W/changed.txt" || ok=0
check "change detection: modified file reported, non-zero exit" $ok

# 7. databases are real tdb files on disk (independent sizes not required,
#    but the changed db must differ from the original content)
[ -s "$DB1" ] && [ -s "$DB3" ] && ! cmp -s "$DB1" "$DB3"
check "db files exist and changed db differs from original" $([ $? -eq 0 ] && echo 1 || echo 0)

echo ""
if [ "$fail" -eq 0 ]; then
    echo "sfic consumer test: 7/7 assertions passed"
else
    echo "sfic consumer test: FAILURES present (see above)"
fi
exit "$fail"
