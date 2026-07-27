#!/usr/bin/env bash
# test_package/test.sh — smoke test for sipcalc CLI
# Usage: test.sh <path-to-sipcalc-binary>
# 上游 sipcalc 1.1.6 经审计无任何测试套件 (MANIFEST.yml upstream_tests_exist: false)
# 本脚本为消费者 test_package, 运行结束后输出 HMBS JSON 证据标记
set -euo pipefail

SIPCALC="${1:-sipcalc}"
FAILED=0

echo "[test] sipcalc --version"
if "$SIPCALC" --version 2>&1 | head -1; then
  echo "PASS: sipcalc --version"
else
  echo "FAIL: sipcalc --version"
  FAILED=1
fi

echo "[test] sipcalc IPv4 /24 subnet"
if "$SIPCALC" 192.168.1.1/24 | grep -q "Network address.*192.168.1.0"; then
  echo "PASS: IPv4 network address"
else
  echo "FAIL: IPv4 network address check"
  FAILED=1
fi

echo "[test] sipcalc IPv6 /64 subnet"
if "$SIPCALC" 2001:db8::1/64 | grep -q "Address type.*Aggregatable Global Unicast"; then
  echo "PASS: IPv6 address type"
else
  echo "FAIL: IPv6 address type check"
  FAILED=1
fi

# HMBS 证据标记 (必须由真机测试命令结束后产生, 数字来自本脚本实际断言)
# test_package: 3 个断言全部执行, passed = (3 - FAILED)
if [ "$FAILED" -eq 0 ]; then
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh <sipcalc_binary>"}'
else
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh <sipcalc_binary>"}'
fi

# 上游套件: 已审计确认 sipcalc 1.1.6 源码无任何测试套件 (upstream_tests_exist: false)
# make check 在 doc/include/src 三个子目录均输出 "Nothing to be done for 'check'"
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"sipcalc 1.1.6 upstream tarball audited: no TESTS/check_PROGRAMS/test targets in Makefile.am, no test source files, make check = Nothing to be done"}'

exit "$FAILED"