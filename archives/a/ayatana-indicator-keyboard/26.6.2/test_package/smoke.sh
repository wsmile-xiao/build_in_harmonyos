#!/usr/bin/env sh
# test_package 冒烟脚本（与 conanfile.py test() 等价；亦可独立于 conan 手动运行）
# 用法: smoke.sh <ayatana-indicator-keyboard-service 可执行文件路径>
set -e
SERVICE="${1:-ayatana-indicator-keyboard-service}"

echo "== $SERVICE --version =="
"$SERVICE" --version | grep -q "ayatana-indicator-keyboard 26.6.2"

echo "== $SERVICE --help =="
"$SERVICE" --help | grep -q "Usage:"

echo "ayatana-indicator-keyboard-service 26.6.2 smoke OK"
