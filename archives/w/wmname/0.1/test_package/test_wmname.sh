#!/bin/sh
# wmname 0.1 消费者测试（R34）——真实执行打包产物并断言行为
# 用法: test_wmname.sh <packaged-wmname-bin> <workdir>
#
# 上游 wmname.c 的确定性分支（本机实测：三条消息均走 stderr，退出码均 1）：
#   argc > 2              → "usage: wmname [name] [-v]"
#   argc == 2 && -v 前缀   → "wmname-0.1, © 2008 Anselm R Garbe"
#   XOpenDisplay(0) == NULL → "wmname: cannot open display"
# 设备/CI 均无 X server，因此必须显式 unset DISPLAY 使第三条分支确定可达。
# 退出码必须恰为 1：126（Operation not permitted＝签名失效）/127（动态库未解析）
# 都会在 A2/A4/A6 当场暴露，等价于断言「已签名 ELF 可加载 + X11 链接正确」。
set -u

BIN="$1"
WORK="${2:-.}"
[ -d "$WORK" ] || WORK="."

[ -x "$BIN" ] || { echo "FAIL: packaged wmname not executable: $BIN"; exit 2; }

# 无 X server 环境：剥离 DISPLAY/XAUTHORITY，保证走确定性错误路径
unset DISPLAY
unset XAUTHORITY

n=0
ok=0
chk() {  # chk <1|0> <描述>
    n=$((n + 1))
    if [ "$1" = "1" ]; then
        ok=$((ok + 1))
        echo "  [ok]   $2"
    else
        echo "  [FAIL] $2"
    fi
}

# A1: 打包产物存在且可执行
chk 1 "A1 packaged bin/wmname exists and is executable"

# A2/A3: 参数错误路径（argc > 2）
"$BIN" a b >"$WORK/wmname_usage.out" 2>&1
rc=$?
[ "$rc" -eq 1 ] && chk 1 "A2 wmname a b exits 1 (got $rc)" || chk 0 "A2 wmname a b exits 1 (got $rc)"
grep -q 'usage: wmname \[name\] \[-v\]' "$WORK/wmname_usage.out"
rc=$?
[ "$rc" -eq 0 ] && chk 1 "A3 usage text 'usage: wmname [name] [-v]' printed" \
                || chk 0 "A3 usage text printed (got: $(cat "$WORK/wmname_usage.out"))"

# A4/A5: 版本路径（argc == 2 且 argv[1] 以 -v 开头）
"$BIN" -v >"$WORK/wmname_version.out" 2>&1
rc=$?
[ "$rc" -eq 1 ] && chk 1 "A4 wmname -v exits 1 (got $rc)" || chk 0 "A4 wmname -v exits 1 (got $rc)"
grep -q 'wmname-0.1' "$WORK/wmname_version.out"
rc=$?
[ "$rc" -eq 0 ] && chk 1 "A5 version string 'wmname-0.1' printed" \
                || chk 0 "A5 version string printed (got: $(cat "$WORK/wmname_version.out"))"

# A6/A7: 无 X 连接失败路径（设置 property 名时 XOpenDisplay(0) 返回 NULL）
"$BIN" LG3D >"$WORK/wmname_nodisplay.out" 2>&1
rc=$?
[ "$rc" -eq 1 ] && chk 1 "A6 wmname LG3D without X server exits 1 (got $rc)" \
                || chk 0 "A6 wmname LG3D without X server exits 1 (got $rc)"
grep -q 'wmname: cannot open display' "$WORK/wmname_nodisplay.out"
rc=$?
[ "$rc" -eq 0 ] && chk 1 "A7 'wmname: cannot open display' message printed" \
                || chk 0 "A7 cannot-open-display message printed (got: $(cat "$WORK/wmname_nodisplay.out"))"

# ── A8/A9/A10: property 名断言（2026-09-30 返修：改为可移植口径）──────────
# 无 X server 时无法现场读写 X property，故对**链接后的打包 ELF** 断言
# wmname.c 使用的三个 atom 名均已成为二进制字面量（XInternAtom 的入参）。
#
# ★ 为什么改：原写法是 `grep -a <字面量> "$BIN"`，判定取决于 **grep 实现对二进制
#   文件的匹配语义**，而不是产物契约（CI PR#13906 红 / 本地绿的根因）：
#     - GNU grep 3.12（本机 /data/service/hnp/bin/grep）→ 命中
#     - toybox 0.8.12（/system/bin/grep；CI 的 test_package 运行环境 PATH 里只有
#       系统 toolbox，没有 buildenv 追加的 hnp 目录）→ 不命中
#   toybox grep 按 C 字符串语义切行：**每行第一个 NUL 之后的字节不可见**
#   （本机实测 'ABC\0\0def' 命中、'def\0\0ABC' 不命中），而 ELF 的 .rodata 字面量
#   都排在 NUL 之后。同一份二进制（包 revision 841175955f…，本地与 CI 逐字节一致）
#   本地 10/10、CI 7/10 ⇒ 原断言测的是工具实现细节，不是产物事实。
#   ⇒ 改法：①把 `strings` 的**纯文本**输出交给 grep（各实现语义一致）；
#           ②保留原始 `grep -a` 作为第二探测器（GNU 环境）；同一事实两种检法，
#             任一命中即通过；③补两条与 grep 无关的产物契约断言 A11/A12。
#   工具按**绝对路径**优先解析，消除对调用方 PATH 的依赖。
STRINGS=/system/bin/strings; [ -x "$STRINGS" ] || STRINGS=$(command -v strings 2>/dev/null || true)
OD=/system/bin/od;           [ -x "$OD" ]      || OD=$(command -v od 2>/dev/null || true)
GREP=/system/bin/grep;       [ -x "$GREP" ]    || GREP=$(command -v grep 2>/dev/null || true)

# has_literal <字面量>：对链接后 ELF 的字符串/字节双探测器搜索
has_literal() {
    if [ -n "$STRINGS" ] && [ -n "$GREP" ] && \
       "$STRINGS" "$BIN" 2>/dev/null | "$GREP" -q -e "$1"; then
        return 0
    fi
    if [ -n "$GREP" ] && "$GREP" -aq -e "$1" "$BIN" 2>/dev/null; then
        return 0
    fi
    return 1
}

has_literal '_NET_WM_NAME'; rc=$?
[ "$rc" -eq 0 ] && chk 1 "A8 binary carries _NET_WM_NAME atom literal (strings|grep)" \
                || chk 0 "A8 binary carries _NET_WM_NAME atom literal (strings|grep)"
has_literal '_NET_SUPPORTING_WM_CHECK'; rc=$?
[ "$rc" -eq 0 ] && chk 1 "A9 binary carries _NET_SUPPORTING_WM_CHECK atom literal (strings|grep)" \
                || chk 0 "A9 binary carries _NET_SUPPORTING_WM_CHECK atom literal (strings|grep)"
has_literal 'UTF8_STRING'; rc=$?
[ "$rc" -eq 0 ] && chk 1 "A10 binary carries UTF8_STRING atom literal (strings|grep)" \
                || chk 0 "A10 binary carries UTF8_STRING atom literal (strings|grep)"

# A11: 动态链接契约 —— 产物内出现 libX11 的 SONAME（.dynstr 的 DT_NEEDED），证明真链
#      X11 而非静态/占位糊弄；与 A2/A4/A6「退出码恰为 1（非 127）」互为佐证
#      （127 = 动态库未解析，加载器根本起不来）。
has_literal 'libX11\.so'; rc=$?
[ "$rc" -eq 0 ] && chk 1 "A11 binary dynamically links libX11 (DT_NEEDED SONAME present)" \
                || chk 0 "A11 binary dynamically links libX11 (DT_NEEDED SONAME present)"

# A12: ELF 头字节级契约（不经 grep，直接用 od 读字节）——ELF64 + 小端 + AArch64
#      e_ident[0:4] = 7f 45 4c 46；e_machine（偏移 18，LE 2 字节）= 0x00b7 = 183
MAGIC=""; MACH=""
if [ -n "$OD" ]; then
    MAGIC=$("$OD" -An -tx1 -j 0 -N 4 "$BIN" 2>/dev/null | tr -d '[:space:]')
    MACH=$("$OD" -An -tx1 -j 18 -N 2 "$BIN" 2>/dev/null | tr -d '[:space:]')
fi
if [ "$MAGIC" = "7f454c46" ] && [ "$MACH" = "b700" ]; then
    chk 1 "A12 ELF header is ELF64/LSB AArch64 (magic=$MAGIC e_machine=$MACH)"
else
    chk 0 "A12 ELF header is ELF64/LSB AArch64 (magic=${MAGIC:-na} e_machine=${MACH:-na})"
fi

# 诊断留痕（不参与计数）：三个 atom 字面量在三种检法下的读数对照，
# 供返修/审计比对「grep -a 是实现相关的；strings|grep 与字节搜索一致」这一事实。
echo "  [info] A8-A10 cross-check readings (grep -a is grep-implementation-dependent):"
for _lit in _NET_WM_NAME _NET_SUPPORTING_WM_CHECK UTF8_STRING; do
    _g=na
    [ -n "$GREP" ] && { "$GREP" -aq -e "$_lit" "$BIN" 2>/dev/null; _g=$?; }
    _s=na
    [ -n "$STRINGS" ] && [ -n "$GREP" ] && { "$STRINGS" "$BIN" 2>/dev/null | "$GREP" -q -e "$_lit"; _s=$?; }
    _p=na
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import sys; d=open(sys.argv[1],"rb").read(); sys.exit(0 if sys.argv[2].encode() in d else 1)' "$BIN" "$_lit" 2>/dev/null
        _p=$?
    fi
    printf '         %-26s grep -a rc=%s | strings|grep rc=%s | python3 rc=%s\n' "$_lit" "$_g" "$_s" "$_p"
done

echo "wmname consumer test: $ok/$n assertions"
[ "$ok" -eq "$n" ] || exit 1
exit 0
