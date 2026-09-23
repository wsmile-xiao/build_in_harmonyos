#!/usr/bin/env bash
# Functionality tests for bsd-finger 0.17 (finger client + in.fingerd).
# NOTE: run via bash (OHOS mksh cannot exec ELF).
# 使用 set -u 而非 set -euo pipefail：check() 逐项捕获子命令退出码并
# 累计 PASS/FAIL（失败继续收集），set -e 会中途退出破坏该模式。
set -u

PASS=0
FAIL=0

check() {
    # check <desc> <expected_substr> <cmd...>
    local desc="$1" expect="$2"
    shift 2
    local out
    out="$("$@" 2>&1)"
    local rc=$?
    if echo "$out" | grep -q "$expect"; then
        PASS=$((PASS+1))
        echo "PASS: $desc"
    else
        FAIL=$((FAIL+1))
        echo "FAIL: $desc (expect substr '$expect', got rc=$rc out='$out')"
    fi
}

# 1. finger with no args: "No one logged on." (rc=0)
check "finger no-args prints No one logged on" "No one logged on" finger

# 2. finger unknown user: "no such user"
check "finger unknown user reports no such user" "no such user" finger no_such_user_xyz

# 3. finger --help: usage text
check "finger --help prints usage" "usage: finger" finger --help

# 4. finger bad option prints usage to stderr
check "finger bad option prints usage" "usage: finger" finger -Z

# 5. finger -l unknown user: per-login format still reports no such user
check "finger -l unknown user reports no such user" "no such user" finger -l no_such_user_xyz

# 6. in.fingerd present and executable
if [ -x "$(command -v in.fingerd 2>/dev/null || echo /nonexistent)" ]; then
    PASS=$((PASS+1)); echo "PASS: in.fingerd present and executable"
else
    FAIL=$((FAIL+1)); echo "FAIL: in.fingerd not executable in PATH"
fi

echo "==================================="
echo "bsd-finger test_package: PASS=$PASS FAIL=$FAIL"
echo "==================================="
[ "$FAIL" -eq 0 ]