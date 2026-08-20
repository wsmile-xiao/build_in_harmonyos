#!/bin/sh
# test_google_authenticator.sh — google-authenticator-libpam 产物验证
#
# 验证 bin/google-authenticator 可执行文件存在且 --version 能正常输出
# （L2 冒烟测试）。用法：test_google_authenticator.sh <cli_path>
set -u

CLI="$1"
if [ ! -f "$CLI" ]; then
    echo "FAIL: google-authenticator binary not found: $CLI"
    exit 1
fi

# --version 输出应非空且包含版本信息（google-authenticator X.YY）
VERSION_OUT="$("$CLI" --version 2>&1)" || {
    echo "FAIL: google-authenticator --version 执行失败"
    exit 1
}
case "$VERSION_OUT" in
    *google-authenticator*|*[0-9]*)
        echo "PASS: google-authenticator --version: $VERSION_OUT"
        ;;
    *)
        echo "FAIL: 意外输出: $VERSION_OUT"
        exit 1
        ;;
esac
exit 0
