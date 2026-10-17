#!/bin/sh
# test.sh — 消费者行为验证：驱动已安装的 fontopia 二进制（非交互用例）
#
# fontopia 是 ncurses TUI，交互界面无法在无终端环境断言；这里用上游自带的
# 非交互入口做真实行为断言：
#   1) --version 打印版本号（fontopia_ver == 2.0）
#   2) --help   打印 "Fontopia for GNU/Linux, Version ..." 横幅 + Usage 段
#   3) 无参数启动时会要求终端（TUI），这里断言它在非 tty 下不会误报版本
#
# 任一断言失败即以非 0 退出，ConanConanFile.test() 随之失败。
set -u

fails=0
checks=0

check() {                       # check <描述> <命令...>
    checks=$((checks + 1))
    if "$@" >/dev/null 2>&1; then
        echo "ok   $checks - $1"
    else
        fails=$((fails + 1))
        echo "FAIL $checks - $1"
    fi
}

# 全部临时产物写到可写临时目录，避免污染配方目录（曾经把 fontopia-help.out 落进
# test_package/ 被误提交）
WORK="${TMPDIR:-$HOME/tmp}/fontopia-test-$$"
mkdir -p "$WORK" 2>/dev/null || WORK="."
cd "$WORK" || exit 1

BIN="$(command -v fontopia || true)"
if [ -z "$BIN" ]; then
    echo "FAIL - fontopia 不在 PATH 中（包未安装或 bindirs 未生效）"
    exit 1
fi
echo "ok   - fontopia = $BIN"

OUT="$("$BIN" --version 2>&1)"
checks=$((checks + 1))
case "$OUT" in
    *2.0*)
        echo "ok   $checks - --version 输出含 2.0（$OUT）"
        ;;
    *)
        fails=$((fails + 1))
        echo "FAIL $checks - --version 输出异常：$OUT"
        ;;
esac

"$BIN" --help > fontopia-help.out 2>&1
HELP="$?"
checks=$((checks + 1))
if [ "$HELP" -eq 0 ]; then
    echo "ok   $checks - --help 退出码 0"
else
    fails=$((fails + 1))
    echo "FAIL $checks - --help 退出码 $HELP"
fi

checks=$((checks + 1))
if grep -q "Fontopia for GNU/Linux, Version" fontopia-help.out; then
    echo "ok   $checks - --help 含版本横幅"
else
    fails=$((fails + 1))
    echo "FAIL $checks - --help 缺版本横幅"
    cat fontopia-help.out
fi

checks=$((checks + 1))
if grep -q "Usage:" fontopia-help.out; then
    echo "ok   $checks - --help 含 Usage 段"
else
    fails=$((fails + 1))
    echo "FAIL $checks - --help 缺 Usage 段"
fi

echo
echo "$checks checks, $fails failures"
[ "$fails" -eq 0 ] || exit 1
exit 0
