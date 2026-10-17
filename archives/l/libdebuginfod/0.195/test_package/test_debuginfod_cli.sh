#!/bin/sh
# CLI 消费者测试:debuginfod-find 真机执行(版本探测 + 不可达服务的优雅失败)
BIN="$1"
test -x "$BIN" || exit 1
"$BIN" --version 2>&1 | head -2 || true
# 对不可达 URL 的查询应非零退出且不挂死
DEBUGINFOD_URLS="http://127.0.0.1:1" DEBUGINFOD_TIMEOUT=2 DEBUGINFOD_RETRY_LIMIT=0 \
  timeout -s KILL 30 "$BIN" debuginfo deadbeef00000001 > out.txt 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then echo "unexpected success"; exit 1; fi
echo "CLI probe OK (find rc=$rc as expected)"
