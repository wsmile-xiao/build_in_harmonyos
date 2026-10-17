#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for zhcon executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

# Locate the installed zhcon binary (bindir follows the conan autotools prefix)
if [ -x "${CONAN_PACKAGE_ROOT:-}/bin/zhcon" ]; then
    ZHCON="${CONAN_PACKAGE_ROOT}/bin/zhcon"
elif [ -x "${CONAN_PACKAGE_ROOT:-}/usr/bin/zhcon" ]; then
    ZHCON="${CONAN_PACKAGE_ROOT}/usr/bin/zhcon"
else
    ZHCON="$(command -v zhcon || true)"
fi
if [ -z "$ZHCON" ] || [ ! -x "$ZHCON" ]; then
    echo "❌ zhcon 可执行文件未找到 (PATH/package root 均无)"
    exit 1
fi
echo "✅ zhcon 可执行文件: $ZHCON"

# Test 1: --version exits 0
echo "[test] zhcon --version"
"$ZHCON" --version >/dev/null 2>&1 || {
    echo "❌ zhcon --version 退出码非 0"
    exit 1
}
echo "✅ --version OK"

# Test 2: --help prints usage banner
echo "[test] zhcon --help"
"$ZHCON" --help 2>&1 | grep -q "zhcon" || {
    echo "❌ zhcon --help 未输出使用说明"
    exit 1
}
echo "✅ --help OK"

# Test 3: zhcon.conf config profile shipped by the package
echo "[test] zhcon.conf"
if [ -n "${CONAN_PACKAGE_ROOT:-}" ] && [ -f "${CONAN_PACKAGE_ROOT}/etc/zhcon.conf" ]; then
    echo "✅ zhcon.conf 存在: ${CONAN_PACKAGE_ROOT}/etc/zhcon.conf"
else
    echo "⚠️ zhcon.conf 不在包内（由系统配置接管）"
fi

# Test 4: input-method data files are required at runtime
echo "[test] 输入法数据"
if [ -d "${CONAN_PACKAGE_ROOT:-}/lib/zhcon/input" ]; then
    MB_COUNT=$(find "${CONAN_PACKAGE_ROOT}/lib/zhcon/input" -name "*.mb" | wc -l)
    [ "$MB_COUNT" -gt 0 ] || {
        echo "❌ 输入法数据目录为空"
        exit 1
    }
    echo "✅ 输入法数据: ${MB_COUNT} 个 .mb 文件"
else
    echo "❌ 输入法数据目录缺失: ${CONAN_PACKAGE_ROOT}/lib/zhcon/input"
    exit 1
fi

echo "zhcon 0.2.6 smoke test: OK"