#!/bin/sh
# cron-apt test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_cron_apt.sh <pkg_dir>
#
# 校验 cron-apt 脚本包完整且可运行：
#   ① bin/cron-apt 存在 + 可执行 + sh -n 语法可解析
#   ② share/cron-apt/functions 已打包（cron-apt 运行时会 source）
#   ③ 运行时真实执行 cron-apt --help，断言输出 USAGE 且退出码 0
#
# 说明：cron-apt 的实际更新功能依赖 apt/apt-get，OHOS 上暂无适配；
#       此处只验证脚本自身可解析、可启动（--help 路径不触碰 apt）。
set -eu

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

BIN="$PKG/bin/cron-apt"
FUNCS="$PKG/share/cron-apt/functions"

if [ ! -f "$BIN" ]; then
    echo "FAIL: bin/cron-apt missing in $PKG" >&2
    exit 1
fi
if [ ! -x "$BIN" ]; then
    echo "FAIL: bin/cron-apt not executable" >&2
    exit 1
fi
echo "OK: bin/cron-apt present and executable"

if [ ! -f "$FUNCS" ]; then
    echo "FAIL: share/cron-apt/functions missing（cron-apt 运行时会 source 它）" >&2
    exit 1
fi
echo "OK: share/cron-apt/functions packaged"

# 语法校验（POSIX sh）
if ! sh -n "$BIN"; then
    echo "FAIL: bin/cron-apt 语法错误" >&2
    exit 1
fi
echo "OK: bin/cron-apt syntax valid (sh -n)"

# 运行时真实执行 --help（该路径不触碰 apt），断言输出含 USAGE
OUT="$("$BIN" --help 2>&1)" || {
    echo "FAIL: cron-apt --help exited non-zero: $OUT" >&2
    exit 1
}
case "$OUT" in
    *USAGE*) : ;;
    *) echo "FAIL: cron-apt --help 未输出 USAGE: $OUT" >&2; exit 1 ;;
esac
echo "OK: cron-apt --help 实际执行并输出用法"
echo "cron-apt test_package PASS ($OUT)"
exit 0
