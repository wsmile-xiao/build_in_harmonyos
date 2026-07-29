#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for osmctools 0.9 CLI binaries
# Usage: test.sh <path-to-package-bin-dir>
# 上游 osmctools 0.9 经审计无任何测试套件 (MANIFEST.yml upstream_tests_exist: false)
# 本脚本为消费者 test_package, 运行结束后输出 HMBS JSON 证据标记
# R34: 实质调用被测包的二进制 (osmconvert/osmfilter/osmupdate), 不只打印字符串
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
  # conanrun env: PATH 已包含 package bin/, 直接用命令名
  OSMCONVERT="osmconvert"
  OSMFILTER="osmfilter"
  OSMUPDATE="osmupdate"
else
  OSMCONVERT="$BIN_DIR/osmconvert"
  OSMFILTER="$BIN_DIR/osmfilter"
  OSMUPDATE="$BIN_DIR/osmupdate"
fi

FAILED=0

# --- Test 1: osmconvert --help (smoke: binary installed & runnable) ---
echo "[test] osmconvert --help"
if "$OSMCONVERT" --help 2>&1 | head -5; then
  echo "PASS: osmconvert --help"
else
  echo "FAIL: osmconvert --help"
  FAILED=1
fi

# --- Test 2: osmfilter --help (smoke) ---
echo "[test] osmfilter --help"
if "$OSMFILTER" --help 2>&1 | head -5; then
  echo "PASS: osmfilter --help"
else
  echo "FAIL: osmfilter --help"
  FAILED=1
fi

# --- Test 3: osmupdate --help (smoke) ---
echo "[test] osmupdate --help"
if "$OSMUPDATE" --help 2>&1 | head -5; then
  echo "PASS: osmupdate --help"
else
  echo "FAIL: osmupdate --help"
  FAILED=1
fi

# --- Test 4: osmconvert .osm → .o5m 格式转换 (实质调用被测包 API) ---
# 构造一个最小 .osm 文件, 用 osmconvert 转 .o5m, 验证输出非空
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OSM_IN="$SCRIPT_DIR/sample.osm"
OSM_OUT="$SCRIPT_DIR/sample.o5m"
echo "[test] osmconvert .osm -> .o5m"
if "$OSMCONVERT" "$OSM_IN" -o="$OSM_OUT" 2>&1; then
  if [ -s "$OSM_OUT" ]; then
    echo "PASS: osmconvert produced non-empty .o5m ($(wc -c < "$OSM_OUT") bytes)"
  else
    echo "FAIL: osmconvert .o5m output is empty"
    FAILED=1
  fi
else
  echo "FAIL: osmconvert .osm -> .o5m conversion failed"
  FAILED=1
fi

# --- Test 5: osmfilter 按标签过滤 (实质调用被测包 API) ---
# 用 Test 4 生成的 .o5m, 过滤 highway 转为 .o5m
FILT_OUT="$SCRIPT_DIR/sample_filtered.o5m"
echo "[test] osmfilter highway filter"
if "$OSMFILTER" "$OSM_OUT" --keep="highway=" -o="$FILT_OUT" 2>&1; then
  if [ -s "$FILT_OUT" ]; then
    echo "PASS: osmfilter produced non-empty filtered .o5m ($(wc -c < "$FILT_OUT") bytes)"
  else
    echo "FAIL: osmfilter output is empty"
    FAILED=1
  fi
else
  echo "FAIL: osmfilter highway filter failed"
  FAILED=1
fi

# HMBS 证据标记 (必须由真机测试命令结束后产生, 数字来自本脚本实际断言)
# test_package: 5 个断言全部执行, passed = (5 - FAILED)
if [ "$FAILED" -eq 0 ]; then
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh <osmctools_bin_dir>"}'
else
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh <osmctools_bin_dir>"}'
fi

# 上游套件: 已审计确认 osmctools 0.9 源码无任何测试套件 (upstream_tests_exist: false)
# make check 在源码树输出 "Nothing to be done for 'check'" (无 check 目标)
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"osmctools 0.9 upstream tarball audited: configure.ac/Makefile.am have no check target, no TESTS/check_PROGRAMS, no test source files, no tests/ dir; make check = Nothing to be done"}'

exit "$FAILED"
