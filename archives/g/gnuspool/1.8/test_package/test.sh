#!/bin/sh
# gnuspool 消费者测试脚本 —— 以使用者身份运行随包发布的工具并断言行为。
#
# 用法: sh test.sh <gspl-cjlist 绝对路径>
# 断言：①二进制可加载随包共享库并正常执行；②打印用法（Usage:）且含工具名；
#       ③不报缺少 help 数据文件（证明 share/gnuspool/help/ 随包发布成功）。

set -u

TOOL="${1:-}"
if [ -z "$TOOL" ]; then
    echo "usage: sh test.sh <gspl-cjlist path>" >&2
    exit 2
fi
if [ ! -x "$TOOL" ]; then
    echo "tool not found or not executable: $TOOL" >&2
    exit 1
fi

# 该工具无参数时打印用法并以用法错误码退出，故捕获输出后忽略退出码
OUT="$("$TOOL" 2>&1 || true)"

if ! printf '%s' "$OUT" | grep -q "Usage:"; then
    echo "FAIL: 用法输出缺失，实际输出：" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi

if ! printf '%s' "$OUT" | grep -q "gspl-cjlist"; then
    echo "FAIL: 输出未包含工具名 gspl-cjlist：" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi

if printf '%s' "$OUT" | grep -q "Cannot find help message file"; then
    echo "FAIL: 工具找不到随包 help 数据（打包不完整）：" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
fi

echo "PASS: gspl-cjlist 可执行且用法输出与随包 help 数据均正常"
