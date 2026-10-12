#!/bin/sh
# consolation test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_consolation.sh <pkg_dir>
#
# 校验 consolation 包可用（真实执行，R34 反空壳）：
#   ① 定位 sbin/consolation（上游 sbin_PROGRAMS）
#   ② `consolation --version` 成功退出（input.c: version(); exit(0)，
#      不触碰 VT，构建机可安全执行）
#   ③ `consolation --help` 成功退出且输出用法（input.c:
#      usage(); exit(0)；输出首行含 "Usage:"）
# 注：守护主循环需要 CONFIG_VT/TTY0，仅在真实设备集成阶段验证，
#     不在本测试范围内。
set -eu

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

# ① 定位守护进程
BIN=""
for d in sbin bin; do
    if [ -x "$PKG/$d/consolation" ]; then
        BIN="$PKG/$d/consolation"
        break
    fi
done
if [ -z "$BIN" ]; then
    echo "FAIL: consolation not found in $PKG/sbin or $PKG/bin" >&2
    exit 1
fi
echo "OK: consolation found -> $BIN"

# ② --version
OUT="$("$BIN" --version 2>&1)" || {
    echo "FAIL: consolation --version 退出非零: $OUT" >&2
    exit 1
}
echo "OK: consolation --version -> $OUT"

# ③ --help（证明二进制能真实运行并输出用法；usage() 首行含 "Usage:"）
HOUT="$("$BIN" --help 2>&1)" || {
    echo "FAIL: consolation --help 退出非零" >&2
    exit 1
}
case "$HOUT" in
    *"Usage:"*) : ;;
    *) echo "FAIL: consolation --help 输出异常（未找到 Usage:）: $HOUT" >&2
       exit 1 ;;
esac
echo "OK: consolation --help 输出用法"

echo "consolation test_package PASS (3 checks)"
exit 0
