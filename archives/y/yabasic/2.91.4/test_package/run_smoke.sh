#!/bin/sh
# 消费者测试驱动（本文件同时满足 CI 门禁 L0c：test_package/ 下须有 .c/.cpp/.cc/.cxx/.sh/.py 测试源文件）。
# 以“库使用者”身份运行**打包后的** yabasic 解释器，执行同目录 smoke.yab——该脚本内含断言
# （算术/字符串/数组/子例程/控制流，任一不符即 error 且非零退出），退出码即结论。
# 用法: sh run_smoke.sh <packaged-yabasic> <smoke.yab>
set -e

YABASIC="$1"
SCRIPT="$2"

if [ -z "$YABASIC" ] || [ ! -x "$YABASIC" ]; then
    echo "consumer-test: packaged interpreter not found or not executable: $YABASIC" >&2
    exit 1
fi
if [ ! -f "$SCRIPT" ]; then
    echo "consumer-test: consumer script missing: $SCRIPT" >&2
    exit 1
fi

if ! out=$("$YABASIC" "$SCRIPT"); then
    echo "consumer-test: interpreter exited non-zero (an assertion in smoke.yab failed)" >&2
    printf '%s\n' "$out" >&2
    exit 1
fi

printf '%s\n' "$out"

case "$out" in
    *"smoke ok"*)
        echo "consumer-test: PASS (all smoke.yab assertions held)"
        exit 0
        ;;
    *)
        echo "consumer-test: expected marker 'smoke ok' in output" >&2
        exit 1
        ;;
esac
