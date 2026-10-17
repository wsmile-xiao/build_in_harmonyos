#!/bin/sh
# test_runner.sh — fastfec test_package 测试脚本（静态文件，过 CI L0c 门禁）
# R34: 实际执行被测包 fastfec 可执行文件，断言退出码 + 输出内容。
# 路径由 conanfile.py test() 通过环境变量 FASTFEC_BIN 注入。
set -u

: "${FASTFEC_BIN:?FASTFEC_BIN not set}"

pass=0
fail=0

ok()  { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }

# assert_contains <描述> <haystack> <needle>
assert_contains() {
  case "$2" in
    *"$3"*) ok "$1" ;;
    *)      bad "$1 — 未找到期望内容: $3" ;;
  esac
}

# 前置检查: 被测二进制必须存在且可执行（L1e 破坏性验证依赖此断言）
if [ ! -x "$FASTFEC_BIN" ]; then
  echo "FAIL: fastfec binary not found or not executable: $FASTFEC_BIN"
  exit 1
fi

echo "[test] 1/4: fastfec (no args) — 应打印 usage 并非零退出"
out=$("$FASTFEC_BIN" 2>&1); code=$?
if [ "$code" -ne 0 ]; then ok "no-args: 非零退出 (exit=$code)"; else bad "no-args: 期望非零退出, 实际 exit=0"; fi
assert_contains "no-args: 打印 Usage" "$out" "Usage:"
assert_contains "no-args: usage 列出 --print-url 标志" "$out" "--print-url"

echo "[test] 2/4: fastfec -x -p 12345678 — 应打印 FEC URL 且退出码 0"
out=$("$FASTFEC_BIN" -x -p 12345678 2>&1); code=$?
if [ "$code" -eq 0 ]; then ok "-x -p: 退出码 0"; else bad "-x -p: 期望 exit=0, 实际 exit=$code"; fi
assert_contains "-x -p: 打印 FEC filing URLs 标题" "$out" "FEC filing URLs:"
assert_contains "-x -p: Primary URL 含 filing id" "$out" "https://docquery.fec.gov/dcdev/posted/12345678.fec"
assert_contains "-x -p: Converted paper URL 含 filing id" "$out" "https://docquery.fec.gov/paper/posted/12345678.fec"

echo "[test] 3/4: fastfec -x -p 87654321 — URL 应随 filing id 动态生成"
out=$("$FASTFEC_BIN" -x -p 87654321 2>&1); code=$?
if [ "$code" -eq 0 ]; then ok "不同 id: 退出码 0"; else bad "不同 id: 期望 exit=0, 实际 exit=$code"; fi
assert_contains "不同 id: URL 动态生成" "$out" "87654321.fec"

echo "[test] 4/4: fastfec -x -p（缺 filing id）— 应打印 usage 并非零退出"
out=$("$FASTFEC_BIN" -x -p 2>&1); code=$?
if [ "$code" -ne 0 ]; then ok "缺 id: 非零退出 (exit=$code)"; else bad "缺 id: 期望非零退出, 实际 exit=0"; fi
assert_contains "缺 id: 打印 Usage" "$out" "Usage:"

echo
echo "结果: $pass 通过, $fail 失败"
if [ "$fail" -gt 0 ]; then
  echo "TESTS FAILED"
  exit 1
fi
echo "ALL TESTS PASSED"
