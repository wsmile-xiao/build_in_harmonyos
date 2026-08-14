#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for lv executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

# Find ncurses/tinfo runtime library path (OHOS SDK has .so.6 but not in default LD_PATH)
LIBDIR=""
for base in /data/service/hnp/ohos-sdk.org /data/service/hnp; do
    found=$(find "$base" -name "libtinfo.so.6" -print -quit 2>/dev/null)
    if [ -n "$found" ]; then
        LIBDIR=$(dirname "$found")
        break
    fi
done
if [ -n "$LIBDIR" ]; then
    # 避免尾随冒号：LD_LIBRARY_PATH 未设置时展开为 "$LIBDIR"，不产生空路径分量
    # （空分量会被 ld.so 解析为当前工作目录，存在共享库劫持风险）
    export LD_LIBRARY_PATH="${LIBDIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

echo "[test] lv -V (version check)"
lv -V && echo "✅ lv -V OK" || {
    echo "❌ lv -V failed"
    exit 1
}

echo "[test] lv -h (help check)"
lv -h > /dev/null 2>&1 && echo "✅ lv -h OK" || {
    echo "[test] lv -h returned non-zero (may be normal for help)"
}

echo "[test] lgrep -V (symlink check)"
lgrep -V > /dev/null 2>&1 && echo "✅ lgrep -V OK" || {
    echo "❌ lgrep -V failed (symlink may be broken)"
    exit 1
}

echo "[test] All smoke tests passed"
