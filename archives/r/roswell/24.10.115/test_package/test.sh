#!/usr/bin/env bash
# test_package for roswell — 实质验证 ros 二进制可执行且版本正确 (R34)
# 鸿蒙 getpwuid() 无 passwd 条目 → homedir() 返回 NULL → 必须设置 ROSWELL_HOME
set -euo pipefail

ROSWELL_HOME="${ROSWELL_HOME:-$HOME/.roswell-test}"
export ROSWELL_HOME
mkdir -p "$ROSWELL_HOME"

echo "=== ros --version ==="
# 上游 opt_version 将版本输出到 stderr（fprintf(stderr,...)），需合并捕获
VERSION_OUTPUT="$(ros --version 2>&1)"
echo "$VERSION_OUTPUT"

# 断言：版本输出必须包含 24.10.115（实质验证被测二进制，R34）
if echo "$VERSION_OUTPUT" | grep -q "24.10.115"; then
  echo "[ok] ros --version 输出版本号 24.10.115"
else
  echo "[fail] ros --version 输出不符合预期: $VERSION_OUTPUT" >&2
  exit 1
fi

echo "test_package PASS"
