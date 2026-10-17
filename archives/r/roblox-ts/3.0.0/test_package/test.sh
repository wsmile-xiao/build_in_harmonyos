#!/bin/sh
# test_package/test.sh — roblox-ts 3.0.0 消费者验证（L1 smoke test）
#
# 用法: test.sh <package_folder>
#
# 上游 npm 发布包已含预编译 JS，本配方 build() 再材质化运行时依赖闭包
# （node_modules）→ 验证 = 完整性 + 与 npm dist 逐字节一致 + 真实执行打包后的
# rbxtsc CLI（R34：不得空壳）。带 [OHOS] 标记的为鸿蒙特有用例。
# 纯 POSIX sh；无 sha256 工具或 node 不可用时对应断言 [skip] 不计失败。
PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

LE="$PKG_FOLDER/libexec/roblox-ts"
D="$PKG_FOLDER/bin"
pass=0
fail=0
skip=0

ok()      { echo "  [ok] $1";   pass=$((pass + 1)); }
bad()     { echo "  [FAIL] $1"; fail=$((fail + 1)); }
skipped() { echo "  [skip] $1"; skip=$((skip + 1)); }

chk() {
    # chk <name> <cmd...>
    name="$1"; shift
    if "$@" >/dev/null 2>&1; then ok "$name"; else bad "$name"; fi
}

# ───────────── 解释器可用性探测（启动器同款候选顺序） ─────────────
# OHOS 上 Node.js v24.13.0 正常 JIT 模式可能直接崩溃（E400），--jitless 为恢复
# 条件；故探测与后续调用统一以 --jitless 为准，并留档正常 JIT 的实测结果。
PROBE_DIR="$(dirname "$0")"
PROBE_LOG="$PROBE_DIR/.node-probe.$$"
PROBE_JS="$PROBE_DIR/.node-probe.$$.js"
printf 'console.log(process.version);\n' > "$PROBE_JS" 2>/dev/null
NODE_BIN=""
for cand in "${RBXTSC_NODE:-}" "$(command -v node 2>/dev/null)" /data/service/hnp/bin/node; do
    [ -n "$cand" ] || continue
    [ -x "$cand" ] || { echo "  [info] $cand not executable"; continue; }
    # --jitless：OHOS 上 node 执行 JS 即崩（E400）；以脚本方式探测（与启动器同款）
    if "$cand" --jitless "$PROBE_JS" > "$PROBE_LOG" 2>&1; then NODE_BIN="$cand"; break; fi
    echo "  [info] $cand probe failed: $(tail -n 3 "$PROBE_LOG" 2>/dev/null | tr '\n' ' ')"
done
rm -f "$PROBE_LOG" "$PROBE_JS" 2>/dev/null

# ─────────────────────────── 1. 打包完整性 ───────────────────────────
chk "bin/rbxtsc present & executable"  test -x "$D/rbxtsc"
chk "libexec out/CLI/cli.js present"  test -s "$LE/out/CLI/cli.js"
chk "libexec out/CLI/index.js present" test -s "$LE/out/CLI/index.js"
chk "libexec package.json present"    test -s "$LE/package.json"
chk "libexec README.md packaged"      test -s "$LE/README.md"
chk "licenses/LICENSE present"        test -s "$PKG_FOLDER/licenses/LICENSE"

if grep -q '"rbxtsc"[[:space:]]*:[[:space:]]*"out/CLI/cli.js"' "$LE/package.json" 2>/dev/null; then
    ok "package.json declares bin.rbxtsc=out/CLI/cli.js"
else
    bad "package.json bin.rbxtsc mapping"
fi

chk "include/Promise.lua present"     test -s "$LE/include/Promise.lua"
chk "include/RuntimeLib.lua present"  test -s "$LE/include/RuntimeLib.lua"

# 运行时依赖闭包必须随包分发（否则 rbxtsc 启动即 MODULE_NOT_FOUND）
for m in typescript kleur yargs chokidar fs-extra resolve \
         @roblox-ts/luau-ast @roblox-ts/path-translator @roblox-ts/rojo-resolver; do
    chk "runtime dep packaged: $m" test -d "$LE/node_modules/$m"
done

NJS=$(find "$LE/out" -name '*.js' 2>/dev/null | wc -l | tr -d ' ')
NDTS=$(find "$LE/out" -name '*.d.ts' 2>/dev/null | wc -l | tr -d ' ')
if [ "$NJS" -ge 200 ] && [ "$NDTS" -ge 200 ]; then
    ok "precompiled js/dts counts (js=$NJS dts=$NDTS)"
else
    bad "precompiled js/dts counts (js=$NJS dts=$NDTS, expect >=200)"
fi

# ─────────────────────── 2. 与 npm dist 逐字节一致 ───────────────────────
sha_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "$1" 2>/dev/null | sed 's/.*= //'
    else
        echo ""
    fi
}
if [ -n "$(sha_of "$LE/package.json")" ]; then
    cmp_sha() { # cmp_sha <name> <file> <expected>
        got=$(sha_of "$2")
        if [ "$got" = "$3" ]; then ok "$1"; else bad "$1 (got=$got)"; fi
    }
    cmp_sha "out/CLI/cli.js == npm dist sha256" \
        "$LE/out/CLI/cli.js" \
        821d6ffc0e8760e6a36d828d02ccfd03160cbdaad881da5c825c0200fc2ed365
    cmp_sha "out/CLI/index.js == npm dist sha256" \
        "$LE/out/CLI/index.js" \
        45a39c44fcb8e67fd030a33f38606078fcccd397e6ff2239325838752641ff12
    cmp_sha "include/RuntimeLib.lua == npm dist sha256" \
        "$LE/include/RuntimeLib.lua" \
        4f7183154d504d5f20e5d20f208b4c6542a712038923665be58c75aafd043f68
else
    skipped "sha256 byte-identical checks (no sha256 tool)"
fi

# ──────────────── 3. 真实执行打包后的 rbxtsc CLI（R34） ────────────────
if [ -n "$NODE_BIN" ]; then
    OUT=$("$D/rbxtsc" --version 2>&1); RC=$?
    case "$OUT" in
        *3.0.0*) if [ "$RC" -eq 0 ]; then ok "rbxtsc --version == 3.0.0"; else bad "rbxtsc --version rc=$RC"; fi ;;
        *) bad "rbxtsc --version output ($OUT)" ;;
    esac

    HELP=$("$D/rbxtsc" --help 2>&1)
    if printf '%s' "$HELP" | grep -q "TypeScript-to-Luau" \
       && printf '%s' "$HELP" | grep -q -- "--project" \
       && printf '%s' "$HELP" | grep -q -- "--watch" \
       && printf '%s' "$HELP" | grep -q -- "--luau"; then
        ok "rbxtsc --help CLI surface (options present)"
    else
        bad "rbxtsc --help CLI surface"
    fi

    # 编译器管线真实运行：非项目目录必须报错退出（非 0），证明不是空壳
    ERROUT=$(cd "$(dirname "$0")" && "$D/rbxtsc" -p ./nonexistent-project-xyz 2>&1); ERC=$?
    if [ "$ERC" -ne 0 ]; then
        ok "rbxtsc rejects invalid project (rc=$ERC)"
    else
        bad "rbxtsc accepted invalid project (rc=0)"
    fi

    chk "node --jitless --check out/CLI/cli.js (syntax)" \
        "$NODE_BIN" --jitless --check "$LE/out/CLI/cli.js"
else
    # 逐条 skip（保证「断言位总数」与 node 可用性无关，便于计数口径统一）
    skipped "rbxtsc --version == 3.0.0 (no working node interpreter)"
    skipped "rbxtsc --help CLI surface (no working node interpreter)"
    skipped "rbxtsc rejects invalid project (no working node interpreter)"
    skipped "node --jitless --check (no working node interpreter)"
fi

# ──────────────────── 4. 鸿蒙特有测试用例 [OHOS] ────────────────────
# [OHOS] 1：启动器不依赖上游 `#!/usr/bin/env node` shebang。
# OHOS 上 /usr/bin/env 在部分运行 uid 下不可执行 → 必须为 POSIX sh 包装。
if head -1 "$D/rbxtsc" 2>/dev/null | grep -q '^#!/bin/sh'; then
    ok "[OHOS] bin/rbxtsc is POSIX sh wrapper (no /usr/bin/env node dependency)"
else
    bad "[OHOS] bin/rbxtsc shebang hardening"
fi

if [ -n "$NODE_BIN" ]; then
    # [OHOS] 2：PATH 首位放一个不可用 node（模拟 OHOS 上 PATH 首位为不可用的
    # 工具链 node）时，打包启动器仍须解析出可用解释器并正常输出 3.0.0。
    FAKEBIN="$PKG_FOLDER/.ohos-test-bin"
    mkdir -p "$FAKEBIN" 2>/dev/null
    printf '#!/bin/sh\nexit 134\n' > "$FAKEBIN/node"
    chmod +x "$FAKEBIN/node" 2>/dev/null
    OUT2=$(PATH="$FAKEBIN:$PATH" "$D/rbxtsc" --version 2>&1); RC2=$?
    case "$OUT2" in
        *3.0.0*) if [ "$RC2" -eq 0 ]; then
                     ok "[OHOS] launcher survives unusable first-on-PATH node"
                 else
                     bad "[OHOS] launcher rc=$RC2 with unusable first-on-PATH node"
                 fi ;;
        *) bad "[OHOS] launcher output with unusable first-on-PATH node ($OUT2)" ;;
    esac
    rm -rf "$FAKEBIN" 2>/dev/null
else
    skipped "[OHOS] runtime launcher test (no working node interpreter in this env)"
fi

# 以下三条 [OHOS] 断言为结构/内容级，始终执行（不依赖 node 运行时可用）
# [OHOS] 3：启动器须显式解析解释器候选（RBXTSC_NODE > PATH > OHOS hnp node），
# 不把执行交给不可用的 PATH 首位 node。
if grep -q 'RBXTSC_NODE' "$D/rbxtsc" 2>/dev/null \
   && grep -q '/data/service/hnp/bin/node' "$D/rbxtsc" 2>/dev/null; then
    ok "[OHOS] launcher resolves interpreter candidates (RBXTSC_NODE > PATH > hnp node)"
else
    bad "[OHOS] launcher interpreter candidate resolution"
fi

# [OHOS] 4：启动器须以 --jitless 运行（OHOS V8 JIT SIGTRAP，知识库 E400）
if grep -q -- '--jitless' "$D/rbxtsc" 2>/dev/null; then
    ok "[OHOS] launcher uses node --jitless (V8 JIT workaround, E400)"
else
    bad "[OHOS] launcher missing --jitless"
fi

# [OHOS] 5：启动器须可被 conan 缓存跨 UID 物化后经 /system/bin/sh 执行（E400 记录
# 的 0750/different-UID 场景）——断言为 POSIX sh 脚本且带 exec 语义。
if grep -q '^exec ' "$D/rbxtsc" 2>/dev/null; then
    ok "[OHOS] launcher uses exec (cross-UID cache materialization safe)"
else
    bad "[OHOS] launcher missing exec"
fi

# [OHOS] 6：启动器带 `set -u`，而 RBXTSC_NODE 通常未设置 —— 必须用 ${RBXTSC_NODE:-}
# 展开，否则执行时以 `RBXTSC_NODE: parameter not set` 中止（CI build #65252 实测命中，
# 本机因 node 不可用跳过运行期用例而漏检）。静态检查，不依赖 node 运行时。
if grep -q '${RBXTSC_NODE:-' "$D/rbxtsc" 2>/dev/null \
   && ! grep -q '"$RBXTSC_NODE"' "$D/rbxtsc" 2>/dev/null; then
    ok "[OHOS] launcher expands unset RBXTSC_NODE safely (\${RBXTSC_NODE:-})"
else
    bad "[OHOS] launcher uses bare \$RBXTSC_NODE under set -u"
fi

echo "=== Results: $pass passed, $fail failed, $skip skipped ==="
[ "$fail" -eq 0 ]
