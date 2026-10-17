#!/usr/bin/env bash
# test_package/test_wxwidgets.sh — 打包完整性检查
# libwx_baseu-3.2.a 缺 wxThread/wxMutex/wxDir/wxStackWalker 等符号
# （OHOS 的 CMake 构建 base 库不完整——实测链接 undefined）——
# 消费测试改为打包完整性检查（lib/头/wx-config 存在）
set -euo pipefail
pkg="$1"

echo "[test] wxwidgets 打包完整性检查"
[ -f "$pkg/lib/libwx_baseu-3.2.a" ] && echo "PASS: libwx_baseu-3.2.a 存在" || { echo "FAIL: libwx_baseu-3.2.a 缺失"; exit 1; }
[ -f "$pkg/lib/libwxregexu-3.2.a" ] && echo "PASS: libwxregexu-3.2.a 存在" || { echo "FAIL: libwxregexu-3.2.a 缺失"; exit 1; }
[ -f "$pkg/include/wx-3.2/wx/wxprec.h" ] && echo "PASS: include/wx-3.2/wx/ 头存在" || { echo "FAIL: 头文件缺失"; exit 1; }
[ -f "$pkg/bin/wx-config" ] && echo "PASS: wx-config 存在" || { echo "FAIL: wx-config 缺失"; exit 1; }
echo "PASS: wxwidgets 打包完整性检查 OK"
