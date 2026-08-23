#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for osm2pgsql 2.3.1
# Usage: test.sh <path-to-package-bin-dir> <path-to-package-share-dir>
#
# 上游 osm2pgsql 2.3.1 自带完整 ctest 单元测试套件 (NoDB 子集 32 用例), 已在
# conanfile.py build() 中接入并通过 (HMBS_UPSTREAM_TEST_RESULT 标记由 build() 输出)。
# 本脚本为消费者侧 test_package: 实质调用被测包二进制 osm2pgsql --version 与
# --help (R34: 不只打印字符串), 并验证 default.style 随包正确安装。
# 运行结束后输出 HMBS_TEST_PACKAGE_RESULT JSON 证据标记。
set -euo pipefail

BIN_DIR="${1:-}"
SHARE_DIR="${2:-}"

if [ -n "$BIN_DIR" ]; then
  OSM2PGSQL="$BIN_DIR/osm2pgsql"
else
  # conanrun env: PATH 已包含 package bin/, 直接用命令名
  OSM2PGSQL="osm2pgsql"
fi
if [ -z "$SHARE_DIR" ]; then
  SHARE_DIR="$(dirname "$BIN_DIR")/share/osm2pgsql"
fi

FAILED=0
PASSED=0

# --- Test 1: osm2pgsql --version (smoke: binary installed & runnable) ---
echo "[test] osm2pgsql --version"
if "$OSM2PGSQL" --version 2>&1 | grep -q "osm2pgsql version 2.3.1"; then
  echo "PASS: osm2pgsql --version"
  PASSED=$((PASSED + 1))
else
  echo "FAIL: osm2pgsql --version"
  FAILED=$((FAILED + 1))
fi

# --- Test 2: osm2pgsql --help (smoke) ---
echo "[test] osm2pgsql --help"
HELP_OUTPUT=$("$OSM2PGSQL" --help 2>&1) || HELP_RC=$?
HELP_RC=${HELP_RC:-0}
if [ "$HELP_RC" -eq 0 ] && [ -n "$HELP_OUTPUT" ] && \
   printf '%s\n' "$HELP_OUTPUT" | grep -qi "osm2pgsql"; then
  echo "PASS: osm2pgsql --help"
  PASSED=$((PASSED + 1))
else
  echo "FAIL: osm2pgsql --help (rc=$HELP_RC, output=${#HELP_OUTPUT} bytes)"
  FAILED=$((FAILED + 1))
fi

# --- Test 3: default.style 随包安装 ---
echo "[test] default.style shipping"
STYLE="$SHARE_DIR/default.style"
if [ -s "$STYLE" ] && grep -q "node" "$STYLE" && grep -q "way" "$STYLE"; then
  echo "PASS: default.style at $STYLE"
  PASSED=$((PASSED + 1))
else
  echo "FAIL: default.style missing/empty at $STYLE"
  FAILED=$((FAILED + 1))
fi

# HMBS 证据标记 (必须由真机测试命令结束后产生, 数字来自本脚本实际断言)
if [ "$FAILED" -eq 0 ]; then
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh <osm2pgsql_bin_dir> <osm2pgsql_share_dir>"}'
else
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh <osm2pgsql_bin_dir> <osm2pgsql_share_dir>"}'
fi

exit "$FAILED"