#!/bin/sh
# test_package/test.sh — smoke test for lomiri-polkit-agent's policykit-agent
# 用法: test.sh <path-to-policykit-agent>
# 真实执行被测二进制: --version（断言输出含 0.3.3）+ --help。
set -u

if [ "$#" -lt 1 ]; then
    echo "[test] 用法: test.sh <path-to-policykit-agent>" >&2
    exit 2
fi
BINARY="$1"

if [ ! -x "$BINARY" ]; then
    echo "[test] ❌ 被测二进制不存在或不可执行: $BINARY" >&2
    exit 1
fi

echo "[test] --version"
OUT="$("$BINARY" --version 2>&1)" || {
    echo "[test] ❌ --version 退出码非 0" >&2
    echo "$OUT" >&2
    exit 1
}
echo "$OUT"
echo "$OUT" | grep -q "lomiri-polkit-agent" || {
    echo "[test] ❌ --version 输出缺少程序名 lomiri-polkit-agent" >&2
    exit 1
}
echo "$OUT" | grep -q "0.3.3" || {
    echo "[test] ❌ --version 输出缺少版本号 0.3.3" >&2
    exit 1
}
echo "[test] ✅ --version 含程序名与版本号 0.3.3"

echo "[test] --help"
HELP="$("$BINARY" --help 2>&1)" || {
    echo "[test] ❌ --help 退出码非 0" >&2
    echo "$HELP" >&2
    exit 1
}
echo "$HELP" | grep -q "Usage:" || {
    echo "[test] ❌ --help 输出缺少 Usage 行" >&2
    exit 1
}
echo "[test] ✅ --help OK"

echo "[test] 全部通过"
exit 0
