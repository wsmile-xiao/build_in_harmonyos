#!/bin/sh
# 消费者测试:真机执行交付的 opustags CLI
set -e
BIN="$1"
test -x "$BIN" || exit 1

# 1) --help 退出 0 且含用法信息
"$BIN" --help > help.out 2>&1
grep -qi "usage" help.out

# 2) 非法文件优雅报错(非 0 退出 + 诊断输出)
if "$BIN" does-not-exist.opus > err.out 2>&1; then
    echo "unexpected success on missing file" >&2
    exit 1
fi
grep -qi "error\|cannot\|no such" err.out

echo "opustags consumer test OK"
