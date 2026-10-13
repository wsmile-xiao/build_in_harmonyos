#!/bin/sh
# interception-tools test_package 真实测试脚本(L0c 要求 test_package 有真实测试源文件)
# 用法: test_interception.sh <pkg_dir>
#
# 校验包可用(真实执行,R34 反空壳):
#   ① 定位 bin/ 下三个工具:udevmon、intercept、uinput
#   ② 各工具 `-h` 成功退出并输出 usage(证明二进制真实可执行,
#      动态依赖 libevdev/libudev/yaml-cpp 均已解析)
set -eu

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: pkg dir not provided or missing: '$PKG'" >&2
    exit 1
fi

for tool in udevmon intercept uinput; do
    if [ -x "$PKG/bin/$tool" ]; then
        echo "OK: $tool found -> $PKG/bin/$tool"
    else
        echo "FAIL: $tool not found in $PKG/bin" >&2
        exit 1
    fi
done

# 各工具 -h:print_usage(stdout) + EXIT_SUCCESS,输出含 "usage:"
for tool in udevmon intercept uinput; do
    OUT="$("$PKG/bin/$tool" -h 2>&1)" || {
        echo "FAIL: $tool -h 退出非零: $OUT" >&2
        exit 1
    }
    case "$OUT" in
        *usage:*) echo "OK: $tool -h 输出用法" ;;
        *) echo "FAIL: $tool -h 输出异常(未找到 usage:): $OUT" >&2
           exit 1 ;;
    esac
done

echo "interception test_package PASS (3 tools verified)"
exit 0
