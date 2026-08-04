#!/data/service/hnp/bin/bash
# lynis test_package smoke test — 验产物结构而非调 lynis 主入口.
# lynis 主入口有 root 属主检查 (安全设计), Conan 沙箱环境非 root 阻断;
# CI worker 上以 root 跑会正常, 但本地验证绕过属主检查验产物结构更稳妥.
set -u

LYNIS_PKG="${1:-}"
pass=0
fail=0

ok () { echo "PASS: $1"; pass=$((pass + 1)); }
no () { echo "FAIL: $1 ($2)"; fail=$((fail + 1)); }

# Test 1: bin/lynis wrapper 存在
if [ -f "${LYNIS_PKG}/bin/lynis" ]; then
    ok "bin/lynis wrapper exists"
else
    no "bin/lynis wrapper exists" "not found"
fi

# Test 2: bin/ps OHOS 兼容 wrapper 存在 (远端 ohos-ps,Toybox ps 缺 procps -C/-ax/-aux)
if [ -f "${LYNIS_PKG}/bin/ps" ]; then
    ok "bin/ps ohos wrapper exists"
else
    no "bin/ps ohos wrapper exists" "not found"
fi

# Test 3: share/lynis/lynis 主入口脚本存在
if [ -f "${LYNIS_PKG}/share/lynis/lynis" ]; then
    ok "share/lynis/lynis entry exists"
else
    no "share/lynis/lynis entry exists" "not found"
fi

# Test 4: share/lynis/lynis shebang 改为 OHOS bash 路径
if head -1 "${LYNIS_PKG}/share/lynis/lynis" | grep -q "^#!/data/service/hnp/bin/bash"; then
    ok "lynis entry shebang OHOS bash"
else
    no "lynis entry shebang OHOS bash" "got $(head -1 "${LYNIS_PKG}/share/lynis/lynis" 2>/dev/null)"
fi

# Test 5: share/lynis/include/ 目录结构完整 (lynis 依赖 include/ 找配置)
if [ -d "${LYNIS_PKG}/share/lynis/include" ] && [ -f "${LYNIS_PKG}/share/lynis/include/consts" ]; then
    ok "include/ tree intact (consts present)"
else
    no "include/ tree intact" "consts missing"
fi

# Test 6: osdetection 含 HarmonyOS 平台检测分支 (远端 0002 uname HarmonyOS 分流)
if grep -q 'HarmonyOS' "${LYNIS_PKG}/share/lynis/include/osdetection" 2>/dev/null; then
    ok "osdetection HarmonyOS branch present"
else
    no "osdetection HarmonyOS branch present" "not found"
fi

# Test 7: include/functions 含 OHOS_PLATFORM 检测 (远端 0001 PSOPTIONS/HMDFS 适配)
if grep -q 'OHOS_PLATFORM' "${LYNIS_PKG}/share/lynis/include/functions" 2>/dev/null; then
    ok "functions OHOS_PLATFORM adaptation present"
else
    no "functions OHOS_PLATFORM adaptation present" "not found"
fi

# Test 8: include/functions 含 LYNIS_OHOS_TRUST_PACKAGE HMDFS 属主信任 (远端 0001)
if grep -q 'LYNIS_OHOS_TRUST_PACKAGE' "${LYNIS_PKG}/share/lynis/include/functions" 2>/dev/null; then
    ok "functions HMDFS trust_package adaptation present"
else
    no "functions HMDFS trust_package adaptation present" "not found"
fi

# Test 9: lynis 主入口含早 --version 处理 (远端 0003 E214 非交互环境)
if grep -q 'Early --version' "${LYNIS_PKG}/share/lynis/lynis" 2>/dev/null; then
    ok "lynis early --version handling present"
else
    no "lynis early --version handling present" "not found"
fi

# Test 10: lynis 主入口含 SCRIPT_DIR 路径检测 (远端 0003 installable paths)
if grep -q 'SCRIPT_DIR' "${LYNIS_PKG}/share/lynis/lynis" 2>/dev/null; then
    ok "lynis SCRIPT_DIR installable paths present"
else
    no "lynis SCRIPT_DIR installable paths present" "not found"
fi

# Test 11: etc/lynis/default.prf 配置文件装好
if [ -f "${LYNIS_PKG}/etc/lynis/default.prf" ]; then
    ok "etc/lynis/default.prf profile installed"
else
    no "etc/lynis/default.prf profile installed" "not found"
fi

# Test 12: wrapper shebang OHOS bash + cd 到 share 目录
if head -1 "${LYNIS_PKG}/bin/lynis" | grep -q "^#!/data/service/hnp/bin/bash" && \
   grep -q 'cd "\$(dirname "\$0")/../share/lynis"' "${LYNIS_PKG}/bin/lynis"; then
    ok "wrapper shebang + cd share contract"
else
    no "wrapper shebang + cd share contract" "wrapper content wrong"
fi

# Test 13: 65 个脚本 shebang 全改 (残留 #!/bin/sh 应为空)
residual=$(grep -rl "^#!/bin/sh" "${LYNIS_PKG}/share/lynis/" 2>/dev/null | wc -l)
if [ "$residual" -eq 0 ]; then
    ok "all scripts shebang OHOS bash (0 residual)"
else
    no "all scripts shebang OHOS bash" "$residual residual #!/bin/sh found"
fi

echo "---"
echo "pass=$pass fail=$fail"
[ $fail -eq 0 ] && exit 0 || exit 1
