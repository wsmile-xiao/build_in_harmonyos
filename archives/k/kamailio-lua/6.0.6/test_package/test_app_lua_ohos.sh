#!/data/service/hnp/bin/bash
# Kamailio-lua 6.0.6 L1 消费者测试（OHOS PC）
# 用法: test_app_lua_ohos.sh <package_folder>
# 被测物: <package_folder>/lib/kamailio/app_lua.so（kamailio 运行期 dlopen 的插件）
#
# 注：仅启用 `set -u`（未用 `set -e`）—— 本脚本需要跑完全部检查项后统一报告
#     （收集 fail 计数并输出完整清单），`set -e` 会在首个失败项处提前退出。
set -u

usage() { echo "usage: $0 <package_folder>" >&2; exit 2; }
[ $# -eq 1 ] || usage
PKG="$1"
MOD="$PKG/lib/kamailio/app_lua.so"

fail=0
ok()   { echo "  [OK]   $1"; }
bad()  { echo "  [FAIL] $1"; fail=1; }

echo "== kamailio-lua 6.0.6 L1 测试 =="
echo "package: $PKG"
echo "module : $MOD"

# 1 产物存在性
if [ -f "$MOD" ]; then
    SZ=$(wc -c < "$MOD" | tr -d ' ')
    if [ "$SZ" -ge 102400 ]; then ok "[1] 产物存在且大小合理（${SZ} bytes）"; else bad "[1] 产物过小（${SZ} bytes）"; fi
else
    bad "[1] 未找到产物 $MOD"
    echo "RESULT: FAIL"; exit 1
fi

READELF=${READELF:-llvm-readelf}
NM=${NM:-llvm-nm}
STRINGS=${STRINGS:-strings}

HDR=$("$READELF" -h "$MOD" 2>&1)
DYNAMIC=$("$READELF" -d "$MOD" 2>&1)
SYMS=$("$NM" -D "$MOD" 2>&1)
RAWSTR=$("$STRINGS" -a "$MOD" 2>&1)

# H1 OHOS ABI 契约（鸿蒙特有用例）
echo "$HDR" | grep -q "ELF64"   && ok "[H1] OHOS ABI: ELF64"                    || bad "[H1] OHOS ABI: 非 ELF64"
echo "$HDR" | grep -q "AArch64" && ok "[H1] OHOS ABI: AArch64（aarch64-linux-ohos）" || bad "[H1] OHOS ABI: 目标架构非 AArch64"
echo "$HDR" | grep -qE "Type:[[:space:]]*DYN" && ok "[H1] OHOS ABI: ET_DYN 共享对象"      || bad "[H1] OHOS ABI: 非 ET_DYN"

# H2 OHOS 依赖自洽（鸿蒙特有用例）
echo "$DYNAMIC" | grep -q "libc.so"   && ok "[H2] OHOS 依赖自洽: NEEDED 含 OHOS libc（libc.so）" || bad "[H2] NEEDED 缺少 libc.so"
if echo "$DYNAMIC" | grep -q "liblua.so"; then
    bad "[H2] 依赖了 liblua.so —— OHOS 无系统 liblua，Lua 必须静态内嵌"
else
    ok "[H2] OHOS 依赖自洽: 无 liblua.so（Lua 已静态内嵌）"
fi

# H3 RPATH 卫生
if echo "$DYNAMIC" | grep -qE "\((RPATH|RUNPATH)\)"; then
    bad "[H3] RPATH 卫生: 残留宿主/构建机路径依赖"
else
    ok "[H3] RPATH 卫生: 无 RPATH/RUNPATH"
fi

# H4 kamailio 模块接口（6.x 加载契约：mod_register + _<mod>_exports）
echo "$SYMS" | grep -qw "mod_register"        && ok "[H4] kamailio 模块接口: mod_register"        || bad "[H4] 缺少 mod_register"
echo "$SYMS" | grep -qw "_app_lua_exports"    && ok "[H4] kamailio 模块接口: _app_lua_exports"    || bad "[H4] 缺少 _app_lua_exports"

# H5 内嵌 Lua 运行时
echo "$SYMS" | grep -qw "luaL_newstate" && ok "[H5] 内嵌 Lua 运行时: luaL_newstate" || bad "[H5] 缺少 luaL_newstate"
echo "$SYMS" | grep -qw "luaL_openlibs" && ok "[H5] 内嵌 Lua 运行时: luaL_openlibs" || bad "[H5] 缺少 luaL_openlibs"
echo "$RAWSTR" | grep -q "Lua 5.4"       && ok "[H5] 内嵌 Lua 运行时: 版本串 Lua 5.4" || bad "[H5] 未见 Lua 5.4 版本串"

# H7 kamailio 模块/core 目标标识一致性（鸿蒙特有用例）
#    kamailio 加载模块时校验 "kamailio <ver> (<arch>/<os>)"，不一致即
#    "module version mismatch" 拒绝加载；OHOS 上 core 按 Linux ABI 构建。
if echo "$RAWSTR" | grep -q "aarch64/linux"; then
    ok "[H7] 模块目标标识: aarch64/linux（与 OHOS 上 core 构建口径一致）"
else
    bad "[H7] 模块目标标识非 aarch64/linux —— 与 core 不一致时 kamailio 将拒绝加载"
fi

# H8 编译标志集合与 OHOS core 口径一致（鸿蒙特有用例）
#    kamailio 同时校验 core/module 的编译标志集合，不一致即拒绝加载。
#    OHOS 上 core 口径 = 关闭 SCTP（sysroot 无 netinet/sctp.h）+ 去掉 HAVE_RESOLV_RES
#    （OHOS libc 无 _res）。
if echo "$RAWSTR" | grep -q "USE_SCTP"; then
    bad "[H8] 编译标志含 USE_SCTP —— 与 OHOS core 口径不一致"
else
    ok "[H8] 编译标志不含 USE_SCTP（OHOS 无 SCTP 支持，与 core 口径一致）"
fi
if echo "$RAWSTR" | grep -q "HAVE_RESOLV_RES"; then
    bad "[H8] 编译标志含 HAVE_RESOLV_RES —— 与 OHOS core 口径不一致"
else
    ok "[H8] 编译标志不含 HAVE_RESOLV_RES（OHOS libc 无 _res，与 core 口径一致）"
fi

if [ "$fail" -ne 0 ]; then echo "RESULT: FAIL"; exit 1; fi
echo "RESULT: PASS"
