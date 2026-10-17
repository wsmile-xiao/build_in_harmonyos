#!/bin/sh
# lsw 0.3 消费者测试（R34）——无 X 环境确定性错误路径断言
# 用法: sh test_lsw_nox.sh <bindir> <output-file-dir>
# 断言: 上游 lsw.c L19-20 —— XOpenDisplay 返回 NULL 时
#       fprintf(stderr, "%s: cannot open display\n", argv[0]); exit(EXIT_FAILURE)
#       （证明 ELF 可执行 + libX11 动态链接链加载正确）
set -e

BIN="$1/lsw"
SPOOL="$2"
OUT="$SPOOL/lsw-test-out.txt"

[ -x "$BIN" ] || { echo "FAIL: $BIN not executable"; exit 2; }
echo "OK 1/2: packaged binary exists and is executable"

# 确保 DISPLAY 不指向任何可达 X server（headless 设备本就无 X）
unset DISPLAY

rc=0
"$BIN" > "$OUT" 2>&1 || rc=$?
[ "$rc" -ne 0 ] || { echo "FAIL: lsw should fail without display, rc=0"; exit 1; }
grep -q "cannot open display" "$OUT" || { echo "FAIL: unexpected output:"; cat "$OUT"; exit 1; }
echo "OK 2/2: no-X error path reported 'cannot open display' with rc=$rc"

echo "ALL 2/2 CONSUMER ASSERTIONS PASSED"
