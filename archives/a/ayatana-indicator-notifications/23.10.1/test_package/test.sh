#!/bin/sh
# test_package/test.sh — smoke test for ayatana-indicator-notifications-service
# 用法: test.sh <path-to-ayatana-indicator-notifications-service>
# 真实执行被测二进制: --version（断言输出含 23.10.1）+ --help。
set -u

if [ "$#" -lt 1 ]; then
    echo "[test] 用法: test.sh <path-to-ayatana-indicator-notifications-service>" >&2
    exit 2
fi
BINARY="$1"

echo "[test] --version"
OUT="$("$BINARY" --version 2>&1)" || {
    echo "[test] ❌ --version 退出码非 0" >&2
    echo "$OUT" >&2
    exit 1
}
echo "$OUT"
echo "$OUT" | grep -q "23.10.1" || {
    echo "[test] ❌ --version 输出缺少版本号 23.10.1" >&2
    exit 1
}
echo "[test] ✅ --version 含版本号 23.10.1"

echo "[test] --help"
"$BINARY" --help >/dev/null 2>&1 || {
    echo "[test] ❌ --help 失败" >&2
    exit 1
}
echo "[test] ✅ --help OK"

echo "[test] 全部通过"
exit 0
