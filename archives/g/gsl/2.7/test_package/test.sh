#!/bin/sh
# GSL 2.7 — HarmonyOS PC 鸿蒙特有测试驱动（rule12：具名端到端消费者用例）
#
# 用法: sh test.sh <runtime-dir>
#   <runtime-dir> 由 test_package/conanfile.py 准备：内含摊平为实体文件的
#   libgsl / libgslcblas .so，以及本次构建产出的 consumer 可执行文件。
#
# 每个用例都是一条完整端到端流程（构造真实输入 → 调 GSL 公开 API → 产出真实结果），
# 本脚本读取 consumer 打印的 VALUE 并与独立参考值逐字比对（校验内容，非空壳打印）。
# 参考值来源：HC-1/2/4/5/6 为手算或教科书值，HC-3 为确定性算法的黄金值。
#
# 关于 set 选项：故意不加 `-e`。本脚本的设计是「逐个用例执行 → 记录 rc → 继续跑完
# 其余用例 → 最后汇总各用例通过/失败」，`-e` 会在第一个失败用例处直接退出，导致
# 剩余用例的失败信息全部丢失。pipefail 保留，/system/bin/sh (mksh) 实测支持。
set -uo pipefail

RUNDIR=${1:?用法: sh test.sh <runtime-dir>}
CONSUMER="$RUNDIR/consumer"

if [ ! -x "$CONSUMER" ]; then
    echo "FATAL: 消费者程序不可执行: $CONSUMER"
    exit 1
fi

TOTAL=0
PASSED=0
FAILED=0

# run_case <用例号> <名称> <参考值>
run_case() {
    cid=$1
    name=$2
    expect=$3
    out=$(LD_LIBRARY_PATH="$RUNDIR" "$CONSUMER" "$cid" 2>&1)
    rc=$?
    set -- $out
    got_id=${1:-}
    got_val=${2:-}
    got_ver=${3:-}
    TOTAL=$((TOTAL + 1))
    if [ "$rc" -eq 0 ] && [ "$got_id" = "$cid" ] \
       && [ "$got_val" = "$expect" ] && [ "$got_ver" = "PASS" ]; then
        PASSED=$((PASSED + 1))
        printf '  [PASS] %s  %s  → 实测值 %s\n' "$cid" "$name" "$got_val"
    else
        FAILED=$((FAILED + 1))
        printf '  [FAIL] %s  (%s)\n' "$cid" "$name"
        printf '         rc=%s  实测 id=%s value=%s verdict=%s  参考值=%s\n' \
               "$rc" "$got_id" "$got_val" "$got_ver" "$expect"
        printf '%s\n' "$out" | while IFS= read -r line; do
            printf '         | %s\n' "$line"
        done
    fi
}

echo "== GSL 2.7 HarmonyOS PC 鸿蒙特有消费者用例 =="

run_case HC-1 "特殊函数：贝塞尔 J0(5) 端到端求值"      "-0.177597"
run_case HC-2 "线性代数：LU 分解解 Ax=b（经 CBLAS）"   "0.800000,1.400000"
run_case HC-3 "随机数：mt19937 固定种子复现序列"       "1608637542,3421126067"
run_case HC-4 "统计：样本均值与总体标准差"             "5.000000,2.000000"
run_case HC-5 "BLAS：dgemm 2x2 矩阵乘法"               "19.000000,22.000000,43.000000,50.000000"
run_case HC-6 "直方图：分箱计数与越界样本丢弃"         "2,1,3,1"

printf '\n鸿蒙消费者用例：%d/%d PASS\n' "$PASSED" "$TOTAL"
if [ "$FAILED" -ne 0 ]; then
    printf '结论 FAIL：%d 个用例未通过\n' "$FAILED"
    exit 1
fi
printf '结论 PASS：全部鸿蒙消费者用例通过\n'
exit 0
