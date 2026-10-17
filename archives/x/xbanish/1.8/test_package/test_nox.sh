#!/bin/sh
# xbanish 1.8 消费者测试（R34）——无 X 环境的确定性错误路径断言
# 用法: test_nox.sh <packaged-xbanish-bin> [output-file]
#
# 断言依据（上游源码坐实，非猜测）：xbanish.c L144-145
#     if (!(dpy = XOpenDisplay(NULL)))
#             errx(1, "can't open display %s", XDisplayName(NULL));
#   ⇒ 无 X server 时：退出码恒为 1，诊断信息恒含 "can't open display"。
#   能看到这条来自 xbanish 自己的消息，即证明：签名后的 ELF 可加载执行，
#   且 libX11 的动态符号解析在真机上成功（否则会在加载期报 "cannot locate
#   symbol" 并以不同退出码结束）。
set -e
BIN="$1"
OUT="${2:-xbanish_nox_out.txt}"

[ -n "$BIN" ] || { echo "FAIL: no binary given"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: $BIN not a file"; exit 2; }

# 明确不给任何 DISPLAY，走 XOpenDisplay(NULL) 的失败分支
env -u DISPLAY -u XAUTHORITY "$BIN" > "$OUT" 2>&1 && rc=0 || rc=$?

echo "xbanish exit rc=$rc"
cat "$OUT"

if [ "$rc" -ne 1 ]; then
	echo "FAIL: expected exit rc=1 (upstream errx), got rc=$rc"
	exit 1
fi
if ! grep -q "can't open display" "$OUT"; then
	echo "FAIL: expected upstream no-X diagnostic, got:"
	cat "$OUT"
	exit 1
fi
echo "xbanish no-X error path OK (ELF runnable + X11 linkage resolved)"
