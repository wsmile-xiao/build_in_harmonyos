#!/bin/bash
# test.sh — clamz L1 消费者测试
# 验证已构建的 clamz 可执行程序的核心 CLI 行为：
#   1) --help 输出 Usage 且退出码为 0
#   2) --version 输出 "Clamz 0.5" 版权头
#   3) 无参数运行时打印 usage 并以非零码退出（无 AMZ 文件输入）
set -u

# VirtualRunEnv (conanrun) 通过 PATH 注入被测包 bin 目录, 直接调用 clamz
CLAMZ="clamz"
fail=0

# 断言 1: --help
help_out="$("$CLAMZ" --help 2>&1)"
help_rc=$?
if [ $help_rc -ne 0 ]; then
  echo "FAIL: clamz --help exit=$help_rc (expected 0)"
  fail=1
elif ! echo "$help_out" | grep -qi "Usage:"; then
  echo "FAIL: clamz --help output missing 'Usage:'"
  fail=1
else
  echo "PASS: clamz --help (rc=0, contains Usage)"
fi

# 断言 2: --version
ver_out="$("$CLAMZ" --version 2>&1)"
ver_rc=$?
if [ $ver_rc -ne 0 ]; then
  echo "FAIL: clamz --version exit=$ver_rc (expected 0)"
  fail=1
elif ! echo "$ver_out" | grep -qi "Clamz 0.5"; then
  echo "FAIL: clamz --version output missing 'Clamz 0.5': $ver_out"
  fail=1
else
  echo "PASS: clamz --version (rc=0, contains Clamz 0.5)"
fi

# 断言 3: 无参数运行 → 上游行为: 打印 "N of N AMZ files downloaded
# successfully." (stderr) 并以 0 退出 (main 循环空转, 无下载任务)
noarg_out="$("$CLAMZ" 2>&1)"
noarg_rc=$?
if [ $noarg_rc -ne 0 ]; then
  echo "FAIL: clamz (no args) exit=$noarg_rc (expected 0)"
  fail=1
elif ! echo "$noarg_out" | grep -qi "downloaded successfully"; then
  echo "FAIL: clamz (no args) output missing 'downloaded successfully': $noarg_out"
  fail=1
else
  echo "PASS: clamz (no args) (rc=$noarg_rc, contains 'downloaded successfully')"
fi

# 断言 4: 无效选项 → usage 且非零退出
bad_out="$("$CLAMZ" --definitely-not-an-option 2>&1)"
bad_rc=$?
if [ $bad_rc -eq 0 ]; then
  echo "FAIL: clamz --definitely-not-an-option exit=0 (expected non-zero)"
  fail=1
elif ! echo "$bad_out" | grep -qi "Usage:"; then
  echo "FAIL: clamz bad option output missing 'Usage:'"
  fail=1
else
  echo "PASS: clamz invalid option (rc=$bad_rc, contains Usage)"
fi

# 断言 5 (鸿蒙特有测试): 验证构建产物为 OHOS arm64 (aarch64) ELF
# PC 鸿蒙平台特有验证——上游 Linux 构建产物为 x86_64，本断言确认
# 适配产物为 aarch64 架构、可在鸿蒙 arm64 设备上执行。
clamz_path="$(command -v "$CLAMZ" 2>/dev/null)"
if [ -z "$clamz_path" ]; then
  echo "FAIL: clamz not found in PATH for arch check"
  fail=1
elif readelf -h "$clamz_path" 2>/dev/null | grep -q "Machine:.*AArch64"; then
  echo "PASS: clamz ELF Machine=AArch64 (OHOS arm64)"
else
  arch_line="$(readelf -h "$clamz_path" 2>/dev/null | grep "Machine:" || echo 'readelf failed')"
  echo "FAIL: clamz 非 aarch64 架构: $arch_line"
  fail=1
fi

if [ $fail -ne 0 ]; then
  echo "test.sh: FAILED"
  exit 1
fi
echo "test.sh: ALL 5 ASSERTIONS PASSED"
exit 0
