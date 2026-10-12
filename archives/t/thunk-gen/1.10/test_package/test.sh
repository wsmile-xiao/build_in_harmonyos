#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# thunk-gen 1.10 —— 消费者视角 test_package 驱动
#
# 只用**包装好的产物**跑一遍下游 dj64dev / comcom64 / fdpp 的真实调用管线：
#
#     <pkg>/bin/thunk_gen/parse_decls.sh  ->  nl -v 0  ->  <pkg>/bin/thunk_gen/thunk_gen
#
# 每一段的期望值都由 src/thunk_gen.y 的文法语义与 scripts/*.sh 的脚本语义
# 推导得出，不引入预置期望文件；第 5 段把生成物真正编译、链接、运行。
#
# 输出最后一行：
#   HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":<bool>,
#                             "command":"bash test.sh <pkg> <cc>",
#                             "discovered":<n>,"passedCount":<n>}
# 退出码：0 = 全部断言通过；1 = 有失败
# ---------------------------------------------------------------------------
set -u
set -o pipefail

PKG="${1:-}"
CC="${2:-clang}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "usage: $0 <package_folder> [cc]" >&2
    exit 1
fi

# 首选上游安装位置（meson libexecdir/datadir，经 MesonToolchain 映射后落在
# bin/thunk_gen 与 res/thunk_gen），找不到时回退全包搜索并把实际路径打印出来，
# 便于在日志里直接看到真实布局。
resolve() {
    _name="$1"; _want="$2"; _fallback="$3"
    for _c in "$_want" "$_fallback"; do
        if [ -f "$_c" ]; then printf '%s' "$_c"; return 0; fi
    done
    _hit=$(find "$PKG" -name "$_name" -type f 2>/dev/null | head -1)
    if [ -n "$_hit" ]; then printf '%s' "$_hit"; return 0; fi
    printf '%s' "$_want"
}

TG=$(resolve thunk_gen "$PKG/bin/thunk_gen/thunk_gen" "$PKG/bin/thunk_gen")
PDS=$(resolve parse_decls.sh "$PKG/bin/thunk_gen/parse_decls.sh" "$PKG/libexec/thunk_gen/parse_decls.sh")
MKADS=$(resolve mkasmdefs.sh "$PKG/bin/thunk_gen/mkasmdefs.sh" "$PKG/libexec/thunk_gen/mkasmdefs.sh")
TGS=$(resolve tg_m4 "$PKG/bin/thunk_gen/tg_m4" "$PKG/libexec/thunk_gen/tg_m4")
TGM4=$(resolve thunks.m4 "$PKG/res/thunk_gen/thunks.m4" "$PKG/share/thunk_gen/thunks.m4")

echo "== 包布局（实测解析结果）=="
echo "  TG    = $TG"
echo "  PDS   = $PDS"
echo "  MKADS = $MKADS"
echo "  TGS   = $TGS"
echo "  TGM4  = $TGM4"

CHECKS=0
FAILS=0
ok()  { CHECKS=$((CHECKS + 1)); printf '  [ok]   %s\n' "$1"; }
bad() { CHECKS=$((CHECKS + 1)); FAILS=$((FAILS + 1)); printf '  [FAIL] %s\n' "$1"; }

check_eq() {  # check_eq <desc> <expected> <actual>
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 [expected=$2 actual=$3]"; fi
}
check_has() { # check_has <desc> <pattern> <file>
    if grep -q -- "$2" "$3" 2>/dev/null; then ok "$1"; else bad "$1 [missing parameter: $2]"; fi
}
count_of() { grep -c -E "$1" "$2" 2>/dev/null || true; }

number_lines() { nl -v 0 < "$1" | sed -E 's/^ *//'; }

# 工作目录：优先 $TMPDIR，其次 /tmp，最后退回当前目录下的隐藏目录；三条路都
# 在退出时（含中断）整目录清理，避免把中间产物遗留在 test_package 里污染提交。
WORK=""
for _base in "${TMPDIR:-}" /tmp ./.tg-consumer-work; do
    [ -n "$_base" ] || continue
    if mkdir -p "$_base/thunk-gen-consumer-$$" 2>/dev/null; then
        WORK="$_base/thunk-gen-consumer-$$"
        break
    fi
done
if [ -z "$WORK" ]; then
    echo "无法创建消费者测试工作目录" >&2
    exit 1
fi
trap 'rm -rf "$WORK"' EXIT INT TERM
echo "  WORK  = $WORK"

echo
echo "== 1) 随包交付的消费者脚本与可执行文件在位 =="
check_eq "thunk_gen 存在" "yes" "$([ -f "$TG" ] && echo yes || echo no)"
check_eq "parse_decls.sh 存在" "yes" "$([ -f "$PDS" ] && echo yes || echo no)"
check_eq "mkasmdefs.sh 存在" "yes" "$([ -f "$MKADS" ] && echo yes || echo no)"
check_eq "tg_m4 存在" "yes" "$([ -f "$TGS" ] && echo yes || echo no)"
check_eq "thunks.m4 存在" "yes" "$([ -f "$TGM4" ] && echo yes || echo no)"

if [ -f "$TG" ] && [ -f "$PDS" ]; then
    echo
    echo "== 2) 筛选器 1（调用侧）：应恰好 4 行 =="
    bash "$PDS" 1 consumer_decls.h > "$WORK/calls.filtered" 2>"$WORK/pds.err" \
        || bad "parse_decls.sh 1 执行失败: $(cat "$WORK/pds.err")"
    check_eq "calls.filtered 行数" "4" "$(wc -l < "$WORK/calls.filtered" | tr -d ' ')"
    check_eq "剔除宏定义干扰行" "0" "$(count_of '^#define' "$WORK/calls.filtered")"
    check_has "含 _dos_open" "_dos_open" "$WORK/calls.filtered"
    check_has "含 _dos_exit" "_dos_exit" "$WORK/calls.filtered"

    echo
    echo "== 3) 编号（nl -v 0）+ thunk_gen(thunk_type=0) 生成 C 派发表 =="
    number_lines "$WORK/calls.filtered" > "$WORK/thunk_calls.tmp"
    check_eq "thunk_calls.tmp 行数" "4" "$(wc -l < "$WORK/thunk_calls.tmp" | tr -d ' ')"
    if "$TG" -a 4 -p 4 < "$WORK/thunk_calls.tmp" > "$WORK/thunk_calls.h" 2>"$WORK/tg.err"; then
        ok "thunk_gen -a 4 -p 4 退出码 0"
    else
        bad "thunk_gen(thunk_type=0) 失败: $(cat "$WORK/tg.err")"
    fi
    check_eq "case 标签数" "4" "$(count_of '^[[:space:]]*case [0-9]+:' "$WORK/thunk_calls.h")"
    check_has "case 1 = _dos_close（返回宽度 4）" \
        '_DISPATCH(4, _ARG_R(UDWORD), _RET, _dos_close' "$WORK/thunk_calls.h"
    check_has "case 0 = _dos_open（void，指针参数）" \
        '_DISPATCH_v(_dos_open, _ARG_PTR(0, const char, _SP)' "$WORK/thunk_calls.h"
    check_eq "定义侧符号不得出现在 C 派发表" "0" "$(count_of '_dos_getfree' "$WORK/thunk_calls.h")"

    echo
    echo "== 4) 定义侧（筛选器 2）+ thunk_type=1 / 2 双形态 =="
    bash "$PDS" 2 consumer_decls.h > "$WORK/asms.filtered" 2>/dev/null
    check_eq "asms.filtered 行数" "2" "$(wc -l < "$WORK/asms.filtered" | tr -d ' ')"
    check_eq "剔除注释干扰行" "0" "$(count_of '^[[:space:]]*//' "$WORK/asms.filtered")"
    number_lines "$WORK/asms.filtered" > "$WORK/thunk_asms.tmp"
    if "$TG" -a 4 -p 4 1 < "$WORK/thunk_asms.tmp" > "$WORK/type1.txt" 2>/dev/null; then
        ok "thunk_gen(thunk_type=1) 退出码 0"
    else
        bad "thunk_gen(thunk_type=1) 失败"
    fi
    # 注意：check_has 走 BRE（grep 无 -E），此处括号是字面字符，不能写成 \(
    check_has "m4 形态 THUNK(0, 0, 1, _P)" '^THUNK(0, 0, 1, _P)$' "$WORK/type1.txt"
    check_has "m4 形态 THUNK(1, 1, 0, _v)" '^THUNK(1, 1, 0, _v)$' "$WORK/type1.txt"
    if "$TG" -a 4 -p 4 2 < "$WORK/thunk_asms.tmp" > "$WORK/type2.txt" 2>/dev/null; then
        ok "thunk_gen(thunk_type=2) 退出码 0"
    else
        bad "thunk_gen(thunk_type=2) 失败"
    fi
    check_has "C++ 宏形态 _THUNK0_P(" '_THUNK0_P(' "$WORK/type2.txt"
    check_has "C++ 宏形态 _THUNK1_v(" '_THUNK1_v(' "$WORK/type2.txt"

    echo
    echo "== 4b) mkasmdefs.sh（asm 侧符号宏）=="
    printf '%s\n' '__ASM(unsigned short, _ds) SEMIC' > "$WORK/glob_asm.h"
    if bash "$MKADS" "$WORK/glob_asm.h" > "$WORK/glob_asmdefs.h" 2>/dev/null; then
        ok "mkasmdefs.sh 退出码 0"
    else
        bad "mkasmdefs.sh 执行失败"
    fi
    check_has "生成 __ASYM_L(_ds)" '__ASYM_L(_ds)' "$WORK/glob_asmdefs.h"

    echo
    echo "== 4c) m4sugar 阶段（tg_m4 + thunks.m4）=="
    if command -v autom4te >/dev/null 2>&1; then
        if bash "$TGS" "$TGM4" < "$WORK/type1.txt" > "$WORK/asms_m4.h" 2>"$WORK/m4.err"; then
            ok "m4 管线退出码 0"
        else
            bad "m4 管线失败: $(head -3 "$WORK/m4.err")"
        fi
        check_has "展开 TG_ABI" '^#define TG_ABI 3' "$WORK/asms_m4.h"
    else
        echo "  [note] 平台未提供 autom4te（下游消费者可选工具），跳过 m4sugar 阶段"
    fi
else
    bad "缺少随包交付的 thunk_gen / parse_decls.sh，跳过后续管线断言"
fi

echo
echo "== 5) 消费者 C 探针：把生成的 thunk_calls.h 真实编译 + 链接 + 运行 =="
PROBE_CHECKS=0
PROBE_PASSED=0
PROBE_FAILS=0
if [ -f test_thunk_gen.c ] && [ -f "$WORK/thunk_calls.h" ]; then
    if "$CC" -O1 -Wall -Wno-unused-function -I"$WORK" -o "$WORK/test_thunk_gen" \
            test_thunk_gen.c > "$WORK/compile.log" 2>&1; then
        ok "消费者探针编译通过（$CC）"
    else
        bad "消费者探针编译失败: $(tail -5 "$WORK/compile.log")"
    fi
    if [ -x "$WORK/test_thunk_gen" ]; then
        "$WORK/test_thunk_gen" > "$WORK/probe.log" 2>&1
        sed -n '1,40p' "$WORK/probe.log"
        PROBE_CHECKS=$(sed -nE 's/^OHOS_CONSUMER_C checks=([0-9]+).*/\1/p' "$WORK/probe.log" | tail -1)
        PROBE_PASSED=$(sed -nE 's/^OHOS_CONSUMER_C .*passed=([0-9]+).*/\1/p' "$WORK/probe.log" | tail -1)
        PROBE_FAILS=$(sed -nE 's/^OHOS_CONSUMER_C .*failed=([0-9]+).*/\1/p' "$WORK/probe.log" | tail -1)
        PROBE_CHECKS=${PROBE_CHECKS:-0}
        PROBE_PASSED=${PROBE_PASSED:-0}
        PROBE_FAILS=${PROBE_FAILS:-0}
        check_eq "探针自报 checks 与 passed 一致" "$PROBE_CHECKS" "$PROBE_PASSED"
    else
        bad "消费者探针未产出可执行文件"
    fi
else
    bad "缺少 test_thunk_gen.c 或生成的 thunk_calls.h，无法进行消费者编译验证"
fi

TOTAL_CHECKS=$((CHECKS + PROBE_CHECKS))
TOTAL_PASSED=$((CHECKS - FAILS + PROBE_PASSED))
TOTAL_FAILS=$((FAILS + PROBE_FAILS))

echo
echo "== 汇总 =="
echo "  test.sh 断言: $CHECKS 通过 $((CHECKS - FAILS)) 失败 $FAILS"
echo "  探针断言:     $PROBE_CHECKS 通过 $PROBE_PASSED 失败 $PROBE_FAILS"

if [ "$TOTAL_FAILS" -eq 0 ] && [ "$TOTAL_CHECKS" -gt 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh <pkg> <cc>","discovered":%d,"passedCount":%d}\n' \
        "$TOTAL_CHECKS" "$TOTAL_PASSED"
    exit 0
fi

printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh <pkg> <cc>","discovered":%d,"passedCount":%d}\n' \
    "$TOTAL_CHECKS" "$TOTAL_PASSED"
exit 1
