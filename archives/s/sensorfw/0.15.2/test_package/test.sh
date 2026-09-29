#!/data/service/hnp/bin/bash
# =============================================================================
# test_package/test.sh — sensorfw 0.15.2 消费者测试（OpenHarmony PC / aarch64）
# =============================================================================
# 由 test_package/conanfile.py 在 conanrun 环境中调用（conan create 阶段执行）。
#   参数 $1 = 本包编译出的消费者测试程序绝对路径
#   参数 $2 = 被测包的 package 目录绝对路径
#   参数 $3 = 日志/临时目录（conan 构建目录，不污染 archives 源码树）
#
# 用例清单（本脚本 3 个 + C++ 程序 3 个 = 6 个）：
#   consumer.ohos.elfarch   产物为 OHOS PC 目标架构 (aarch64) 的 ELF
#   consumer.ohos.packaging 包内不含任何符号链接，且版本化 SONAME 布局完整
#   consumer.daemon.help    bin/sensorfwd --help 真实执行并输出用法（退出码 0）
#   consumer.api.types      ↓ 以下 3 个由 test_sensorfw 输出 [result] 行
#   consumer.api.qtmeta
#   consumer.ohos.dlopen    **鸿蒙特有**：包内全部插件以 RTLD_NOW 打开并解析成功
#
# 为什么要先「解引用重定位」再运行：
#   本平台加载器在**程序启动阶段解析 DT_NEEDED 名字**时，如果搜索路径里首个
#   命中的条目是 `.so` 版本化**符号链接**，会报
#     Error loading shared library <name>: (needed by <binary>)
#   即把该条目当成「不存在」而使启动失败。实测对照（同一批文件、同一来源）：
#     · 符号链接 + 对应实体（libQt5DBus.so.5 -> libQt5DBus.so.5.15.19）→ 启动失败
#     · 全部为实体文件（cp -L 解引用后）                              → 启动成功
#   进程内 dlopen 不受此限：同一个符号链接用 dlopen("<裸名>")（LD_LIBRARY_PATH
#   指向该目录）或 dlopen("<完整路径>") 在独立进程里均成功 —— 该限制只出现在
#   启动期解析路径上。
#   Conan 包内的 libQt5*.so.5 恰是符号链接（`QMAKE_LN_SHLIB = cp -f` 只作用于
#   sensorfw 自己的产物），所以直接把包目录当 LD_LIBRARY_PATH 会失败。
#   这里按 DT_NEEDED 闭包把库 `cp -L` 解引用到可写目录后再运行。
#   两条排除是实测必需：系统库目录不复制（否则 timeout 等系统程序自身加载
#   失败），/system/lib64/libc.so 绝不复制（会破坏 musl 的 libc 绑定）。
# =============================================================================
set -u

BIN="${1:?usage: test.sh <test-binary> <package-folder> [log-dir]}"
PKG="${2:?usage: test.sh <test-binary> <package-folder> [log-dir]}"

LOGDIR=""
for _c in "${3:-}" "${TMPDIR:-}" "$PWD"; do
    [ -n "$_c" ] || continue
    [ -d "$_c" ] || continue
    [ -w "$_c" ] || continue
    LOGDIR="$_c"
    break
done
[ -n "$LOGDIR" ] || LOGDIR="$PWD"

READELF="$(command -v readelf 2>/dev/null || echo /data/service/hnp/bin/readelf)"

CASE_TOTAL=0
CASE_PASS=0
CASE_FAIL=0
ASSERT_PASS=0
ASSERT_FAIL=0

ok()  { echo "     ok   $*";  ASSERT_PASS=$((ASSERT_PASS + 1)); }
bad() { echo "     FAIL $*";  ASSERT_FAIL=$((ASSERT_FAIL + 1)); }
case_result() { # $1=用例名 $2=ok|fail
    CASE_TOTAL=$((CASE_TOTAL + 1))
    if [ "$2" = ok ]; then
        CASE_PASS=$((CASE_PASS + 1)); printf '  ==> 用例 %-26s : PASS\n' "$1"
    else
        CASE_FAIL=$((CASE_FAIL + 1)); printf '  ==> 用例 %-26s : FAIL\n' "$1"
    fi
}

echo "=============================================================="
echo "sensorfw 0.15.2 消费者测试 (OHOS aarch64)"
echo "  测试程序 : $BIN"
echo "  被测包   : $PKG"
echo "  日志目录 : $LOGDIR"
echo "=============================================================="

# ── 解引用重定位目录 ────────────────────────────────────────────────────────
RELOC="$LOGDIR/sensorfw-consumer-libs.$$"
rm -rf "$RELOC" 2>/dev/null || true
mkdir -p "$RELOC" || { echo "无法创建重定位目录 $RELOC"; exit 1; }

# 依赖库搜索目录：conanrun 注入的 LD_LIBRARY_PATH（被测包 lib/ + qt lib/）
# 之外，必须再加上包内的插件目录 —— 补丁 0005 让 libcompasschain-qt5.so 记录了
# 对 libavgaccfilter / libdownsamplefilter / libdeclinationfilter /
# libmagcalibrationchain 的 DT_NEEDED，而这四个模块与它同住在
# lib/sensord-qt5/ 里，并不在 libdirs 上，只查 LD_LIBRARY_PATH 会漏掉，
# 表现为 dlopen 失败：
#   Error loading shared library libavgaccfilter-qt5.so
#   (needed by .../lib/sensord-qt5/libcompasschain-qt5.so)
SEARCH_DIRS="$PKG/lib:$PKG/lib/sensord-qt5:${LD_LIBRARY_PATH:-}"

relocate_one() { # $1=ELF 文件；把它自身及其 DT_NEEDED 闭包解引用复制到 $RELOC
    local queue item name path
    queue="$1"
    while [ -n "$queue" ]; do
        item="${queue%% *}"
        if [ "$item" = "$queue" ]; then queue=""; else queue="${queue#* }"; fi
        [ -n "$item" ] || continue
        for name in $("$READELF" -d "$item" 2>/dev/null \
                       | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p'); do
            [ -e "$RELOC/$name" ] && continue
            path=""
            local old_ifs="$IFS"; IFS=:
            for d in $SEARCH_DIRS; do
                if [ -e "$d/$name" ]; then path="$d/$name"; break; fi
            done
            IFS="$old_ifs"
            [ -n "$path" ] || continue
            case "$path" in
                /system/*|/vendor/*|/lib/*|/lib64/*|/usr/lib/*) continue ;;
            esac
            cp -L "$path" "$RELOC/$name" 2>/dev/null || true
            queue="$queue $RELOC/$name"
        done
    done
}

# 以「包内所有 ELF 产物」为根展开闭包：测试程序、守护进程、全部库与全部插件。
# 插件是运行期 dlopen 的，其 DT_NEEDED（含 0004 补丁带来的 libsensorfw-qt5）
# 也必须就位。
ROOTS="$BIN $PKG/bin/sensorfwd"
for f in "$PKG"/lib/*.so* "$PKG"/lib/*/*.so*; do
    [ -e "$f" ] || continue
    ROOTS="$ROOTS $f"
done
for root in $ROOTS; do
    [ -e "$root" ] && relocate_one "$root"
done
RELOC_COUNT="$(ls -1 "$RELOC" 2>/dev/null | wc -l)"
echo "  重定位库目录: $RELOC ($RELOC_COUNT libs)"
echo

# =============================================================================
# 用例 1: consumer.ohos.elfarch
# =============================================================================
echo "  [case] consumer.ohos.elfarch"
elf_ok=1
for f in "$PKG/bin/sensorfwd" "$BIN" \
         "$PKG/lib/libsensorfw-qt5.so.0.9.0" "$PKG/lib/sensord-qt5/libaccelerometeradaptor-qt5.so"; do
    if [ ! -f "$f" ]; then bad "缺少产物 $f"; elf_ok=0; continue; fi
    if ! "$READELF" -h "$f" 2>/dev/null | grep -q 'AArch64'; then
        bad "$(basename "$f") 不是 AArch64 ELF"; elf_ok=0
    fi
done
[ "$elf_ok" -eq 1 ] && ok "bin/sensorfwd、测试程序与库/插件均为 AArch64 ELF"
case_result consumer.ohos.elfarch $([ "$elf_ok" -eq 1 ] && echo ok || echo fail)

# =============================================================================
# 用例 2: consumer.ohos.packaging  —— 包内不得有符号链接，且 SONAME 布局完整
# =============================================================================
echo "  [case] consumer.ohos.packaging"
pkg_ok=1
symlinks="$(find "$PKG" -type l 2>/dev/null | wc -l)"
if [ "$symlinks" -eq 0 ]; then
    ok "包内 0 个符号链接（加载器拒绝符号链接，故打包必须打平）"
else
    bad "包内存在 $symlinks 个符号链接，加载器会拒绝这些库"
    find "$PKG" -type l 2>/dev/null | head -5 | while read -r l; do echo "       $l"; done
    pkg_ok=0
fi
for lib in libsensorfw-qt5 libsensordatatypes-qt5 libsensorclient-qt5; do
    ver_count="$(ls -1 "$PKG/lib/$lib.so"* 2>/dev/null | wc -l)"
    if [ "$ver_count" -ge 3 ]; then
        ok "$lib 版本化 SONAME 布局完整（$ver_count 个实体文件）"
    else
        bad "$lib 版本化 SONAME 布局不完整（仅 $ver_count 个文件）"; pkg_ok=0
    fi
done
plugin_count="$(ls -1 "$PKG"/lib/sensord-qt5/*.so 2>/dev/null | wc -l)"
if [ "$plugin_count" -ge 40 ]; then
    ok "lib/sensord-qt5/ 插件齐备（$plugin_count 个）"
else
    bad "lib/sensord-qt5/ 插件缺失（仅 $plugin_count 个）"; pkg_ok=0
fi

# 头文件布局必须与上游 install 规则（也就是上游 sensord-qt5.pc 的
# Cflags: -I${includedir} -I${includedir}/datatypes）完全一致：
# 除 datatypes/ 外一律平铺，且**不存在** filters/ 与 core/ 子目录
# （filters.pro 的 publicheaders.files = *.h 零匹配，qmake 没生成安装规则；
#   core.pro 的 path 追加也未生效，生成的规则目标是平铺路径）。
INC_ROOT="$PKG/include/sensord-qt5"
if [ -f "$INC_ROOT/datatypes/xyz.h" ]; then
    ok "头文件 datatypes/ 子目录存在（datatypes/xyz.h）"
else
    bad "缺少 $INC_ROOT/datatypes/xyz.h"; pkg_ok=0
fi
if [ -f "$INC_ROOT/abstractchain.h" ]; then
    ok "core 头文件按上游规则平铺（abstractchain.h）"
else
    bad "缺少平铺的 $INC_ROOT/abstractchain.h"; pkg_ok=0
fi
for stray in filters core; do
    if [ -d "$INC_ROOT/$stray" ]; then
        bad "多出上游不存在的 include 子目录 $stray/（上游 install 无此布局）"
        pkg_ok=0
    fi
done
if [ ! -d "$INC_ROOT/filters" ] && [ ! -d "$INC_ROOT/core" ]; then
    ok "无上游不存在的 include 子目录（filters/ core/ 均不存在）"
fi
if [ -z "$(find "$PKG/include" -name 'moc_predefs.h' 2>/dev/null)" ]; then
    ok "未混入 qmake 生成物（无 moc_predefs.h）"
else
    bad "包内混入 qmake 生成物 moc_predefs.h"
    pkg_ok=0
fi
case_result consumer.ohos.packaging $([ "$pkg_ok" -eq 1 ] && echo ok || echo fail)

# =============================================================================
# 用例 3: consumer.daemon.help —— 守护进程可执行且能自省
# =============================================================================
echo "  [case] consumer.daemon.help"
HELP_LOG="$LOGDIR/sensorfw-sensorfwd-help.log"
LD_LIBRARY_PATH="$RELOC:${LD_LIBRARY_PATH:-}" "$PKG/bin/sensorfwd" --help \
    >"$HELP_LOG" 2>&1
help_rc=$?
if [ "$help_rc" -eq 0 ] && grep -q 'Usage: sensord' "$HELP_LOG"; then
    ok "sensorfwd --help 退出码 0 且输出用法（日志 $HELP_LOG）"
    case_result consumer.daemon.help ok
else
    bad "sensorfwd --help 退出码 $help_rc（日志 $HELP_LOG）"
    sed -n '1,5p' "$HELP_LOG" | while read -r l; do echo "       $l"; done
    case_result consumer.daemon.help fail
fi

# =============================================================================
# C++ 消费者程序：consumer.api.types / consumer.api.qtmeta / consumer.ohos.dlopen
# =============================================================================
echo
CPP_LOG="$LOGDIR/sensorfw-consumer.log"
LD_LIBRARY_PATH="$RELOC:${LD_LIBRARY_PATH:-}" "$BIN" "$PKG/lib/sensord-qt5" \
    >"$CPP_LOG" 2>&1
cpp_rc=$?
cat "$CPP_LOG"

# 解析 "  [result] <name> PASS|FAIL checks=N failed=M"（与 C++ 程序约定的输出协议）
# 注意：这里**不能**用 `while ... done < <(sed ...)`（bash 进程替换）—— 本脚本可能被
# 以 `$CONFIG_SHELL`（值为 /bin/sh = mksh）调用，mksh 不支持该语法，会直接
# `syntax error: unexpected '< '` 并让整个 test() 以 exit 1 失败（2026-09-27 实测踩到）。
# 故改成「先落临时文件，再重定向读」的纯 POSIX 写法。
RESULT_LINES="$LOGDIR/sensorfw-consumer-results.txt"
sed -n 's/^  \[result\] \([^ ]*\) \([A-Z]*\) checks=\([0-9]*\) failed=\([0-9]*\)$/\1 \2 \3 \4/p' \
    "$CPP_LOG" > "$RESULT_LINES"
cpp_cases=0
while read -r cname cverdict cchecks cfailed; do
    [ -n "$cname" ] || continue
    cpp_cases=$((cpp_cases + 1))
    case_result "$cname" "$([ "$cverdict" = PASS ] && echo ok || echo fail)"
    ASSERT_PASS=$((ASSERT_PASS + ${cchecks#checks=} - ${cfailed#failed=}))
    ASSERT_FAIL=$((ASSERT_FAIL + ${cfailed#failed=}))
done < "$RESULT_LINES"

if [ "$cpp_cases" -lt 3 ]; then
    bad "消费者程序只报告了 $cpp_cases 个用例（应为 3），可能提前退出"
    [ "$cpp_cases" -eq 0 ] && case_result consumer.api.types fail
    [ "$cpp_cases" -eq 1 ] && case_result consumer.api.qtmeta fail
    [ "$cpp_cases" -eq 2 ] && case_result consumer.ohos.dlopen fail
fi
# 与程序自身的汇总行交叉校验（防止解析协议失配被静默忽略）
cpp_total="$(sed -n 's/^== checks: \([0-9]*\) passed: \([0-9]*\) failed: \([0-9]*\)$/\1 \2 \3/p' "$CPP_LOG" | tail -1)"
if [ -z "$cpp_total" ]; then
    bad "消费者程序未输出汇总行（退出码 $cpp_rc）"
else
    set -- $cpp_total
    echo "     （交叉校验：程序自报 checks=$1 passed=$2 failed=$3，退出码=$cpp_rc）"
    [ "$cpp_rc" -eq 0 ] || bad "消费者程序退出码 $cpp_rc（应含失败断言）"
fi
echo "     （消费者程序日志: $CPP_LOG）"

# =============================================================================
echo
echo "=============================================================="
printf '用例: 总 %d / 通过 %d / 失败 %d\n' "$CASE_TOTAL" "$CASE_PASS" "$CASE_FAIL"
printf '断言: 通过 %d / 失败 %d\n' "$ASSERT_PASS" "$ASSERT_FAIL"
echo "=============================================================="

[ "$CASE_FAIL" -eq 0 ] && [ "$ASSERT_FAIL" -eq 0 ]
