#!/bin/sh
# clipnotify 1.0.2 消费者测试（R34）——无 X 环境确定性错误路径断言
# 用法: test_nox.sh <packaged-clipnotify-bin> [output-file]
# 断言: 上游 clipnotify.c L13-16 —— XOpenDisplay 失败时 exit(1) 且
#       输出 "Can't open X display"（证明 ELF 可执行 + X11 链接正确）
set -e
BIN="$1"
OUT="${2:-clipnotify_out.txt}"
[ -x "$BIN" ] || { echo "FAIL: $BIN not executable"; exit 2; }
"$BIN" > "$OUT" 2>&1 || rc=$?
rc=${rc:-0}
echo "clipnotify exit rc=$rc"
[ "$rc" -eq 1 ] || { echo "FAIL: unexpected exit rc=$rc"; exit 1; }
grep -q "Can't open X display" "$OUT" || { echo "FAIL: unexpected output:"; cat "$OUT"; exit 1; }
echo "clipnotify no-X error path OK"
