#!/bin/sh
# HarmonyOS 专项测试 — cohomcalg 0.32
# 验证: 在 OHOS (clang/clang++) 工具链下编译的 cohomcalg 二进制,
#       对上游样例输入 dP1/dP3/CP2 输出的线丛上同调维数结果与数学预期一致。
# 禁止空测试: 断言实际数学输出内容, 非仅检查退出码。

set -u
BIN="${1:-./bin/cohomcalg}"
SRC_DIR="${2:-.}"
TEST_TMP="${3:-$HOME/tmp/cohomcalg-ohos-test}"
PASS=0
FAIL=0

mkdir -p "$TEST_TMP"

check_case() {
    name="$1"; input="$2"; expected="$3"
    out="$TEST_TMP/$name.out"
    timeout 120 "$BIN" --integrated --nomonomfile "$SRC_DIR/bin/$input" > "$out" 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "[FAIL] $name: 运行退出码=$rc (期望 0)"
        FAIL=$((FAIL+1)); return
    fi
    if grep -Fq "$expected" "$out"; then
        echo "[PASS] $name: 输出含预期上同调结果"
        PASS=$((PASS+1))
    else
        echo "[FAIL] $name: 输出未含预期 '$expected'"
        FAIL=$((FAIL+1))
    fi
}

echo "== HarmonyOS 专项测试: cohomcalg 0.32 (OHOS 工具链产物) =="
echo "BIN=$BIN  SRC_DIR=$SRC_DIR  $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# dP1 (del Pezzo-1): O(-1,-2)/(O(-2,0)/O(-3,-2)) 上同调 = (0,1,0),(0,1,0),(0,0,1)
check_case dP1_ohos dP1.in '{{0,1,0},{{1,1*u3*u4}}}'
check_case dP1_ohos_b dP1.in '{{0,0,1},{{2,1*u1*u2*u3*u4}}}'
# dP3 (del Pezzo-3): O(0,2,0) 期望 (0,2,0)
check_case dP3_ohos dP3.in '{{0,2,0},{{1,1*u1*u2*u5}'
# CP2: O(0,0,1) 期望 (0,0,1)
check_case CP2_ohos CP2.in '{{0,0,1},{{2,1*u1*u2*u3}}}'
# P31SU7: 期望 {{1,0,0,0,0,0},{{0,1*1}}}
check_case P31SU7_ohos P31SU7.in '{{1,0,0,0,0,0},{{0,1*1}}}'

echo ""
echo "== 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] && echo "ALL_OHOS_TESTS_PASSED" || echo "OHOS_TESTS_FAILED"
[ "$FAIL" -eq 0 ]
