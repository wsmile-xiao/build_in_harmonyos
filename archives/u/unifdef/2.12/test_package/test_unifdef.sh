#!/bin/sh
# test_package/test_unifdef.sh — functional test for the packaged unifdef binary.
# Runs in the conanrun environment (PATH includes the installed bin/ dir).
# Real assertions on CLI output and on the documented exit statuses
# (0 = output unchanged, 1 = output changed, 2 = error); any failure makes
# `conan test` fail (CI L1e verifies the test really needs the package).
#
# NOTE: deliberately not `set -e`: every assertion runs commands that are
# expected to return non-zero (e.g. unifdef exits 1 when the output changed),
# and the check() helper evaluates them as conditions; errexit would abort
# the suite instead of recording the assertion result.
set -u

DIR="unifdef-test.$$"
mkdir -p "$DIR"
cd "$DIR" || exit 1

n_ok=0
n_fail=0
check() {
  msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

echo "1..12"

cat > basic.c <<'EOF'
#ifdef FOO
int foo(void);
#else
int bar(void);
#endif
EOF

cat > nested.c <<'EOF'
#ifdef OUTER
#ifndef INNER
int nested(void);
#endif
#endif
EOF

# 1) version banner (-V), exit status 0
check "-V prints the unifdef-2.12 banner" \
  'rc=0; out=$(unifdef -V 2>&1) || rc=$?; [ $rc -eq 0 ] && echo "$out" | grep -q "unifdef-2.12"'

# 2) -h prints usage, exit status 0
check "-h prints usage" \
  'rc=0; out=$(unifdef -h 2>&1) || rc=$?; [ $rc -eq 0 ] && echo "$out" | grep -q "usage:"'

# 3) -DFOO keeps the true branch and drops the #else branch
check "-DFOO keeps the #ifdef branch" \
  'unifdef -DFOO basic.c > basic.out; grep -q "int foo(void);" basic.out && ! grep -q "int bar(void);" basic.out && ! grep -q "#ifdef" basic.out'

# 4) -UFOO keeps the #else branch
check "-UFOO keeps the #else branch" \
  'unifdef -UFOO basic.c > undef.out; grep -q "int bar(void);" undef.out && ! grep -q "int foo" undef.out'

# 5) documented exit status: 1 when the output differs from the input
check "exit status 1 when output changes" \
  'rc=0; unifdef -DFOO basic.c > /dev/null || rc=$?; [ $rc -eq 1 ]'

# 6) documented exit status: 0 and untouched output when nothing changes
check "exit status 0 when input is unchanged" \
  'rc=0; unifdef basic.c > unchanged.out || rc=$?; [ $rc -eq 0 ] && cmp -s basic.c unchanged.out'

# 7) -s lists the controlling symbol
check "-s lists the control symbol FOO" \
  'out=$(unifdef -s basic.c); [ "$out" = "FOO" ]'

# 8) nested conditionals: OUTER alone resolves only the outer directive
check "nested #ifndef kept with only OUTER defined" \
  'unifdef -DOUTER nested.c > nested1.out; grep -q "int nested(void);" nested1.out && grep -q "#ifndef INNER" nested1.out'

# 9) nested conditionals: OUTER+INNER remove the inner block
check "nested #ifndef removed with OUTER and INNER defined" \
  'unifdef -DOUTER -DINNER nested.c > nested2.out; [ ! -s nested2.out ]'

# 10) -m modifies the file in place (content equals the filtered output)
check "-m modifies in place" \
  'cp basic.c mod.c; unifdef -DFOO -m mod.c; cmp -s mod.c basic.out'

# 11) -M~ keeps a backup of the original
check "-M~ leaves a backup file" \
  'cp basic.c mod2.c; unifdef -DFOO -M~ mod2.c; cmp -s mod2.c~ basic.c && cmp -s mod2.c basic.out'

# 12) unifdefall wrapper installed and executable
check "unifdefall wrapper is installed and executable" \
  'test -x "$(command -v unifdefall)"'

cd ..
rm -rf "$DIR"
echo "# unifdef functional assertions: pass=$n_ok fail=$n_fail"
[ "$n_fail" -eq 0 ]
