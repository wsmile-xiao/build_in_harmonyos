#!/bin/sh
# test.sh — cppp 2.9 packaged-binary smoke test (consumer perspective).
#
# Runs the installed cppp binary against 4 real usage checks:
#   1. cppp --version produces non-empty version text
#   2. cppp --help produces usage text
#   3. cppp -DFOO keeps an #ifdef FOO-guarded block
#   4. cppp -UFOO drops an #ifdef FOO-guarded block
# Each PASS/FAIL line is printed; the script exits with the number of
# failed checks (0 = all pass).  Invoked as `sh test.sh <cppp>`.

CPPP="${1:-cppp}"

pass=0
fail=0

# check <desc> <exit-status-of-check>
check() {
    desc="$1"
    rc="$2"
    if [ "$rc" -eq 0 ]; then
        echo "PASS: $desc"
        pass=$((pass + 1))
    else
        echo "FAIL: $desc"
        fail=$((fail + 1))
    fi
}

# 1. version
"$CPPP" --version >/dev/null 2>&1
check "cppp --version runs" "$?"

# 2. help
"$CPPP" --help 2>&1 | grep -q "Usage: cppp"
check "cppp --help shows usage" "$?"

# 3. -DFOO keeps guarded block
out=$(printf '#ifdef FOO\nhello\n#endif\n' | "$CPPP" -DFOO 2>&1)
[ "$out" = "hello" ]
check "-DFOO keeps #ifdef FOO block" "$?"

# 4. -UFOO drops guarded block
out2=$(printf '#ifdef FOO\nhello\n#endif\n' | "$CPPP" -UFOO 2>&1)
[ -z "$out2" ]
check "-UFOO drops #ifdef FOO block" "$?"

echo ""
echo "test.sh: $pass/$((pass + fail)) checks passed"
exit "$fail"