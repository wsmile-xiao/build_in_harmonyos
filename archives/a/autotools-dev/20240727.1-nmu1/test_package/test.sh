#!/bin/bash
# autotools-dev test_package — 真实调用打包的 config.sub 断言 OHOS 三元组规范化
# 断言用例取自上游 testsuite/config-sub.data（含 aarch64-linux-ohos 用例）
set -eu

: "${CONFIG_SUB:?CONFIG_SUB must point to packaged config.sub}"

pass=0
fail=0

check() {
    alias_name="$1"
    expected="$2"
    actual=$("$CONFIG_SUB" "$alias_name")
    if [ "$actual" = "$expected" ]; then
        echo "PASS: config.sub $alias_name -> $actual"
        pass=$((pass + 1))
    else
        echo "FAIL: config.sub $alias_name -> $actual (expected $expected)"
        fail=$((fail + 1))
    fi
}

# 1. OHOS 三元组规范化（上游 testsuite 同款用例）
check "aarch64-linux-ohos" "aarch64-unknown-linux-ohos"
# 2. 常见 GNU/Linux 三元组
check "x86_64-linux-gnu" "x86_64-pc-linux-gnu"
# 3. 幂等性：canonical 三元组应映射到自身
check "aarch64-unknown-linux-ohos" "aarch64-unknown-linux-ohos"

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
