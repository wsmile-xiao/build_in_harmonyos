#!/bin/sh
# dwz test_package 真实测试脚本（L0c 要求 test_package 有真实测试源文件）
# 用法: test_dwz.sh <bindir>
# 校验 dwz 二进制存在 + 可执行 + --version 运行（运行时真实执行）
# 审查修复（2026-09-11）：按规则 25 改用 set -euo pipefail；同时去掉首行提取处的
# 管道（改用参数展开），避免 pipefail 下 head 提前关闭管道产生 SIGPIPE 干扰。
set -euo pipefail
BINDIR="${1:-}"
if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "FAIL: bindir not provided or missing: '$BINDIR'" >&2
    exit 1
fi
DWZ="$BINDIR/dwz"
if [ ! -f "$DWZ" ]; then
    echo "FAIL: dwz binary missing in $BINDIR" >&2
    exit 1
fi
if [ ! -x "$DWZ" ]; then
    echo "FAIL: dwz not executable ($DWZ)" >&2
    exit 1
fi
echo "OK: dwz present and executable in $BINDIR"
# 运行时真实执行 --version（验证动态链接库可加载）
VER="$( "$DWZ" --version 2>&1 )" || {
    echo "FAIL: dwz --version exited non-zero" >&2
    exit 1
}
# 取首行（参数展开，不用管道）
NL='
'
FIRST="${VER%%"$NL"*}"
echo "dwz test_package PASS ($FIRST)"
exit 0
