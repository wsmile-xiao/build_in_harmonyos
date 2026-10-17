#!/bin/sh
# test_package 冒烟测试：验证 akku CLI 可执行且输出正确版本。
# akku 用 version 子命令（非 --version，srfi-37 args-fold 解析）。
set -e

VERSION_OUTPUT="$(akku version 2>/dev/null)"
echo "akku version => ${VERSION_OUTPUT}"

case "$VERSION_OUTPUT" in
    *1.1.0*)
        echo "PASS: akku version 输出匹配 1.1.0"
        ;;
    *)
        echo "FAIL: 期望包含 1.1.0，实际输出: ${VERSION_OUTPUT}" >&2
        exit 1
        ;;
esac

HELP_OUTPUT="$(akku help 2>&1)"
case "$HELP_OUTPUT" in
    *"Akku.scm 1.1.0"*"USAGE: akku"* )
        echo "PASS: akku help 输出包含版本和用法"
        ;;
    *)
        echo "FAIL: akku help 未输出预期说明" >&2
        exit 1
        ;;
esac

case "${AKKU:-}" in
    */akku)
        test -x "$AKKU"
        echo "PASS: AKKU 环境变量指向可执行文件"
        ;;
    *)
        echo "FAIL: AKKU 环境变量未指向 akku 可执行文件: ${AKKU:-<unset>}" >&2
        exit 1
        ;;
esac
