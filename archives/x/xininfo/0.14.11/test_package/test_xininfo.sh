#!/bin/bash
# test_xininfo.sh — xininfo 0.14.11 消费者测试（R34：实质执行打包二进制）
#
# 用法: test_xininfo.sh <packaged-bin> <bin-dir> <package-folder> <out-dir>
#
# 平台事实（2026-09-25 B 机鸿蒙 PC 实测，见 archives/x/xininfo/0.14.11/notes.md）：
#   DISPLAY 为空；Xvfb / Xephyr / Xwayland / man 均不在 PATH ⇒ 无法执行任何
#   需要 X server 的功能测试。故本脚本的断言面为「确定性可复算」的四类：
#   ELF 可加载性、签名同源性、无 X 时的上游确定性错误代码路径、
#   X11 三库链接与符号可用性、产物完整性。
#   上游 xininfo.c 行为依据（同一 tarball，行号可复验）：
#     L361-364  -h/-help → help() → execlp("man",...) → return 0
#     L313-321  help(): execlp 失败时 fprintf "Failed to execute man: %s"
#     L369-374  XOpenDisplay 失败 → fprintf "cannot open display!" → EXIT_FAILURE(1)
set -u

BIN="${1:-}"
BINDIR="${2:-}"
PKG="${3:-}"
OUT="${4:-/tmp/xininfo-test-out}"

READELF="$(command -v readelf || echo /data/service/hnp/bin/readelf)"
NM="$(command -v nm || echo /data/service/hnp/bin/nm)"

if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "FAIL: packaged binary not available: ${BIN:-<empty>}"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"test_xininfo.sh","discovered":0,"passedCount":0}\n'
    exit 1
fi
mkdir -p "$OUT" 2>/dev/null || OUT="$BINDIR/../xininfo-out.$$"
mkdir -p "$OUT" 2>/dev/null || true

# EXPECTED = 本 harness 声明的断言条数（A1..A6）；checked = 实际执行到的条数，
# 由 ok()/bad() 各自增一次。两者不等即在收尾处判失败（见 report 段）。
EXPECTED=6
checked=0
passed=0
failed=0
ok()   { checked=$((checked + 1)); passed=$((passed + 1)); echo "[OK]   $1"; }
bad()  { checked=$((checked + 1)); failed=$((failed + 1)); echo "[FAIL] $1"; }
note() { echo "[note] $1"; }

# ---------------------------------------------------------------- A1
# 打包产物是 aarch64 动态可执行 ELF（真机链接产物，非宿主 x86 残留）
if "$READELF" -h "$BIN" > "$OUT/a1.txt" 2>&1 \
   && grep -q "Machine:.*AArch64" "$OUT/a1.txt" \
   && grep -qE "Type:.*(DYN|EXEC)" "$OUT/a1.txt"; then
    ok "A1 packaged binary is an AArch64 ELF executable"
else
    bad "A1 packaged binary is not an AArch64 ELF (see $OUT/a1.txt)"
    sed -n '1,12p' "$OUT/a1.txt"
fi

# ---------------------------------------------------------------- A2
# E077：产物含 .codesign 段（未签名的外来 ELF 会被鸿蒙内核拒绝执行；
# 段缺失 => 即便编译通过也跑不起来，正是 rc=126/EPERM 的来源）
if "$READELF" -S "$BIN" > "$OUT/a2.txt" 2>&1 && grep -q "\.codesign" "$OUT/a2.txt"; then
    ok "A2 .codesign section present in the packaged ELF (E077 self-signature shipped)"
else
    bad "A2 no .codesign section in packaged ELF (unsigned => not executable on OHOS)"
    sed -n '1,20p' "$OUT/a2.txt"
fi

# ---------------------------------------------------------------- A3
# 上游帮助代码路径真实执行：-h/-help -> help() -> execlp("man", ...)
# PATH 锁到包内 bin 目录 => man 必然不可执行 => 确定性打印
# "Failed to execute man: ..." 且 main() return 0（xininfo.c L361-364, L313-321）
env -u DISPLAY PATH="$BINDIR" "$BIN" -h > "$OUT/a3.txt" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "Failed to execute man" "$OUT/a3.txt"; then
    ok "A3 '-h' reaches help() and hits the deterministic execlp(man) failure path (rc=0)"
else
    bad "A3 unexpected '-h' behaviour rc=$rc, expected rc=0 + 'Failed to execute man'"
    sed -n '1,10p' "$OUT/a3.txt"
fi

# ---------------------------------------------------------------- A4
# 无 X server 的上游确定性错误路径（xininfo.c L369-374）：
# XOpenDisplay 失败 => "cannot open display!" + EXIT_FAILURE(1)
# 这条断言同时证明 libX11 已被动态加载、XOpenDisplay 符号已解析并真实执行。
env -u DISPLAY PATH="$BINDIR" "$BIN" > "$OUT/a4.txt" 2>&1
rc=$?
if [ "$rc" -eq 1 ] && grep -q "cannot open display!" "$OUT/a4.txt"; then
    ok "A4 no-X error path reached through the real libX11 (rc=1, 'cannot open display!')"
else
    bad "A4 unexpected no-X behaviour rc=$rc (expected 1 + 'cannot open display!')"
    sed -n '1,10p' "$OUT/a4.txt"
fi

# ---------------------------------------------------------------- A5
# X11 三库链接 + 符号可用性：
#   (a) DT_NEEDED 里确有 libX11 / libXrandr / libXinerama
#   (b) 二进制对三个库的入口符号是未定义引用（真的调用了它们）
#   (c) 每个符号都能在 DT_NEEDED 闭包内的某个 .so 里找到定义
# 依据 xininfo.c L41(Xlib)/L44(Xrandr)/L45(Xinerama) 与 L370/L325/L208 的调用点。
"$READELF" -d "$BIN" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' > "$OUT/a5_needed.txt"
"$NM" -u "$BIN" 2>/dev/null | awk '{print $NF}' | sort -u > "$OUT/a5_undef.txt"
a5_fail=""
for lib in libX11 libXrandr libXinerama; do
    grep -q "$lib" "$OUT/a5_needed.txt" || a5_fail="$a5_fail missing-need:$lib"
done
# 把每个未定义符号在 DT_NEEDED 闭包里逐个求解
: > "$OUT/a5_defined.txt"
IFS=':' read -r -a libdirs <<< "${LD_LIBRARY_PATH:-}"
for l in $(cat "$OUT/a5_needed.txt"); do
    for d in "${libdirs[@]}"; do
        [ -n "$d" ] || continue
        if [ -f "$d/$l" ]; then
            "$NM" -D --defined-only "$d/$l" 2>/dev/null | awk '{print $NF}' >> "$OUT/a5_defined.txt"
            break
        fi
    done
done
sort -u -o "$OUT/a5_defined.txt" "$OUT/a5_defined.txt"
for s in XOpenDisplay XRRGetScreenResources XineramaIsActive; do
    grep -qx "$s" "$OUT/a5_undef.txt"   || a5_fail="$a5_fail not-undefined:$s"
    grep -qx "$s" "$OUT/a5_defined.txt" || a5_fail="$a5_fail unresolved:$s"
done
if [ -z "$a5_fail" ]; then
    ok "A5 libX11/libXrandr/libXinerama are DT_NEEDED and XOpenDisplay/XRRGetScreenResources/XineramaIsActive resolve inside that closure"
else
    bad "A5 X11 link/symbol audit failed:$a5_fail"
fi
# 佐证（不计入断言数）：LD_BIND_NOW 下的即时绑定同样不得报缺符号
env -u DISPLAY LD_BIND_NOW=1 PATH="$BINDIR" "$BIN" > "$OUT/a5b.txt" 2>&1
if grep -q "cannot open display!" "$OUT/a5b.txt"; then
    note "LD_BIND_NOW=1 run also reached the no-X path (corroboration only, not counted)"
else
    note "LD_BIND_NOW=1 run inconclusive on this loader (not counted, not a failure)"
fi

# ---------------------------------------------------------------- A6
# 产物完整性：manpage 已按 Makefile L25 的 INSTALL_MANPAGE 相对布局安装
MAN="$PKG/share/man/man1/xininfo.1"
if [ -s "$MAN" ] && grep -qi "XININFO" "$MAN"; then
    ok "A6 man page installed at share/man/man1/xininfo.1 (non-empty, titles xininfo)"
else
    bad "A6 man page missing or empty: $MAN"
fi

# ---------------------------------------------------------------- report
# discovered 不再写常量：它就是本趟实际执行到的断言条数。
# 任一条断言分支整体未执行（工具缺失、提前退出等）=> checked < EXPECTED
# => 本行下面那个 or 条件成立 => rc=1，"跳过"不可能被记成 6/6。
discovered=$checked
echo "assertions_declared=$EXPECTED assertions_executed=$checked"
echo "discovered=$discovered passed=$passed failed=$failed"
if [ "$failed" -ne 0 ] || [ "$checked" -ne "$EXPECTED" ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xininfo.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"make","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xininfo 0.14.11 上游无测试套件：官方 tag archive 仅 6 个文件（Makefile/LICENSE/doc/xininfo.1/doc/xininfo.markdown/source/xininfo.c/.gitignore），无 tests/ 或 test/ 目录；Makefile 全文无 check/test 目标、无 TESTS 变量（目标仅 all/clean/indent/dist/install，L66/L96/L98/L103/L106）"}\n'
    exit 1
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xininfo.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"make","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xininfo 0.14.11 上游无测试套件：官方 tag archive 仅 6 个文件，无 tests/ 目录；Makefile 无 check/test 目标、无 TESTS 变量（目标仅 all/install/clean/indent/dist）"}\n'
echo "OK: all $discovered consumer checks passed"
exit 0
