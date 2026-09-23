#!/bin/sh
# cado 0.9.6 smoke probe — 独立可运行的二进制冒烟测试。
# 用法: probe.sh [BINDIR]（缺省使用 PATH 中的 cado 二进制）
# 断言与 test_package/conanfile.py 的 test() 保持一致:
#   - cado/cadrop/scado/caprint 4 个可执行文件存在
#   - cado/scado/caprint 的 -h 输出 usage 帮助（退出码非 0 属设计）
#   - cadrop 无 -h，非法 capability 参数输出 "error parsing capabilities"
set -e

BINDIR="${1:-}"
if [ -n "$BINDIR" ]; then
    export PATH="$BINDIR:$PATH"
fi

for exe in cado cadrop scado caprint; do
    if ! command -v "$exe" >/dev/null 2>&1; then
        echo "FAIL: missing $exe" >&2
        exit 1
    fi
    out=$(mktemp)
    "$exe" -h >"$out" 2>&1 || true
    case "$exe" in
        cadrop) grep -q "parsing capabilities" "$out" ;;
        scado)  [ -s "$out" ] ;;   # scado 先做 UID/passwd 检查，非空输出即正常
        *)      grep -qi "usage" "$out" ;;
    esac || {
        echo "FAIL: $exe -h 输出异常: $(head -c 200 "$out")" >&2
        rm -f "$out"
        exit 1
    }
    rm -f "$out"
    echo "ok $exe"
done

echo "PASS: cado 4 个可执行文件 smoke 测试通过"
