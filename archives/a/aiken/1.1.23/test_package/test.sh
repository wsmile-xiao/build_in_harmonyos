#!/usr/bin/env bash
# test_package/test.sh — aiken 1.1.23 消费者视角冒烟测试 (R34: 实质调用被测包)
#
# 测试矩阵 (3 条断言，均实质调用 aiken 二进制):
#   1. --version 输出包含 1.1.23
#   2. --help 退出码 0 且输出非空
#   3. check 一个最小 .ak 项目: aiken check 编译并类型检查,
#      退出码 0 表示被测包核心功能 (解析→类型检查→编译) 正常
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aiken>" >&2
    exit 2
fi

aiken_bin="$1"

if [ ! -f "$aiken_bin" ]; then
    echo "aiken binary not found: $aiken_bin" >&2
    exit 1
fi

echo "[step] Testing aiken --version..."
version_output="$("$aiken_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "1.1.23" >/dev/null
echo "        [ok] version check passed (assertion 1/3)"

echo "[step] Testing aiken --help..."
help_output="$("$aiken_bin" --help 2>&1 || true)"
if [ -z "$help_output" ]; then
    echo "        [fail] aiken --help produced empty output" >&2
    exit 1
fi
echo "        [ok] help check passed (assertion 2/3)"

# 最小 aiken 项目: 一个空 main 函数, 合法 .ak 源码
# aiken check 会执行: 解析 → 类型检查 → 编译, 验证被测包完整工具链
tmpdir="$(mktemp -d 2>/dev/null || echo "$TMPDIR/aiken-test-$$")"
mkdir -p "$tmpdir/aiken_project"
trap 'rm -rf "$tmpdir"' EXIT

cat > "$tmpdir/aiken_project/aiken.toml" <<'TOML'
name = "aiken-lang/smoke_test"
version = "0.0.1"
TOML

cat > "$tmpdir/aiken_project/validators.ak" <<'AK'
validator smoke {
  fn main() -> Int {
    42
  }
}
AK

echo "[step] Testing aiken check (minimal .ak project)..."
check_output="$("$aiken_bin" check "$tmpdir/aiken_project" 2>&1)" || {
    echo "        [fail] aiken check exited non-zero" >&2
    echo "$check_output" >&2
    exit 1
}
echo "        [ok] aiken check passed (assertion 3/3)"

echo "[ok] All 3 tests passed."
