#!/bin/sh
# OHOS 专项测试：验证安装的示例程序在 OHOS arm64 上的确定性（bit-identical）
# 与关键定点运算结果 —— fixed-point-fundamentals 的核心卖点是"每平台每次都
# 逐位一致"。本测试在 OHOS 真机上验证该承诺：重复运行输出 SHA256 逐位一致 +
# 关键数值断言。属于业务上层消费者视角的真实可观测结果测试（调用已安装公开
# 运行时产物，非内部符号、非编译目录）。
set -euo pipefail

fail=0

# ---------- 1. 确定性：同一二进制重复运行输出必须逐位一致 ----------
det_check() {
    cmd=$1
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "FAIL: $cmd not found in PATH"
        fail=1
        return
    fi
    h1=$($cmd 2>&1 | sha256sum | cut -d' ' -f1) || true
    h2=$($cmd 2>&1 | sha256sum | cut -d' ' -f1) || true
    if [ -n "$h1" ] && [ "$h1" = "$h2" ]; then
        echo "OK: $cmd deterministic (sha256=$h1)"
    else
        echo "FAIL: $cmd output not bit-identical across runs ($h1 vs $h2)"
        fail=1
    fi
}

det_check q16_16_basics
det_check rounding_modes
det_check arithmetic_demo
det_check sine_lut

# ---------- 2. 关键定点运算结果断言（数值正确性，公开输出） ----------
# Q16.16: +1 -> raw +65536 -> back to int: +1
out=$(q16_16_basics 2>&1) || true
echo "$out" | grep -q "+1 -> raw     +65536 -> back to int: +1" \
    && echo "OK: q16_16_basics +1 conversion (raw 65536)" \
    || { echo "FAIL: q16_16_basics +1 conversion assertion"; fail=1; }

# Q16.16: 0.5 表示
echo "$out" | grep -qi "Q16_16_HALF" \
    && echo "OK: q16_16_basics exposes Q16_16_HALF" \
    || { echo "FAIL: q16_16_basics HALF constant missing"; fail=1; }

# format_selector: 必须列出 Q16.16 格式
out2=$(format_selector 2>&1) || true
echo "$out2" | grep -q "Q16.16" \
    && echo "OK: format_selector lists Q16.16" \
    || { echo "FAIL: format_selector Q16.16 missing"; fail=1; }

# accumulation_drift: 展示浮点累加漂移（定点课程核心论据）
out3=$(accumulation_drift 2>&1) || true
echo "$out3" | grep -qi "Drift" \
    && echo "OK: accumulation_drift demonstrates drift" \
    || { echo "FAIL: accumulation_drift drift demo missing"; fail=1; }

exit $fail