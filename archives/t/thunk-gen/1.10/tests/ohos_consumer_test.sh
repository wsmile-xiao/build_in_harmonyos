#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# thunk_gen 消费者（consumer）测试驱动 —— OHOS 适配新增
#
# 目的：在目标平台（OHOS / aarch64）上真实执行 thunk_gen 交付给使用者的
#       那条“消费者管线”，也就是 dj64dev / comcom64 / fdpp 一类下游工程
#       实际调用的命令序列：
#
#           scripts/parse_decls.sh  ->  nl/sed 编号  ->  thunk_gen
#
#       四个模式各自覆盖管线的一段：
#         parse-decls   交付给消费者的 shell 脚本（parse_decls.sh /
#                       mkasmdefs.sh）在 OHOS 的 toybox 工具链下的行为
#         gen-c         thunk_type=0 的 C 派发表生成（消费者直接编译的产物）
#         asm-templates thunk_type=1（m4 模板）与 thunk_type=2（C++ 宏）的
#                       生成契约，并做两阶段一致性交叉校验
#         m4-pipeline   把 thunk_type=1 的产物喂给 scripts/tg_m4 +
#                       scripts/thunks.m4，验证 m4sugar 模板阶段。
#                       该阶段依赖 autoconf 的 autom4te（属下游消费者工具，
#                       不是 thunk_gen 自身的构建依赖），平台缺失时返回 77
#                       （meson 记为 SKIP）并打印原因。
#
# 断言口径：所有被检查的文本都由“本次构建出的” thunk_gen 现场生成；期望值由
# src/thunk_gen.y 的文法语义与 scripts/*.sh 的脚本语义推导得出，不使用预置
# 期望文件，避免自证。
#
# 退出码：0 = 全部通过；1 = 有断言失败；77 = 平台缺可选工具而 SKIP；2 = 用法错
# ---------------------------------------------------------------------------
set -u
set -o pipefail

MODE="${1:-}"
TGBIN="${2:-}"
SRCDIR="${3:-}"
WORKDIR="${4:-}"
OUTFILE="${5:-}"

if [ -z "$MODE" ] || [ -z "$TGBIN" ] || [ -z "$SRCDIR" ] || [ -z "$WORKDIR" ]; then
    echo "usage: $0 <parse-decls|gen-c|asm-templates|m4-pipeline> <thunk_gen> <src_dir> <work_dir> [out_file]" >&2
    exit 2
fi

DECLS="$SRCDIR/ohos_consumer_decls.h"
PDS="$SRCDIR/../scripts/parse_decls.sh"
MKADS="$SRCDIR/../scripts/mkasmdefs.sh"
TGS="$SRCDIR/../scripts/tg_m4"
TGM4="$SRCDIR/../scripts/thunks.m4"

for f in "$DECLS" "$PDS" "$MKADS" "$TGS" "$TGM4"; do
    if [ ! -f "$f" ]; then
        echo "missing required input: $f" >&2
        exit 2
    fi
done
if [ ! -x "$TGBIN" ]; then
    echo "thunk_gen not executable: $TGBIN" >&2
    exit 2
fi

mkdir -p "$WORKDIR" || exit 2

CHECKS=0
FAILS=0

note() { printf '%s\n' "$*"; }
ok()   { CHECKS=$((CHECKS + 1)); note "  [ok]   $1"; }
bad()  { CHECKS=$((CHECKS + 1)); FAILS=$((FAILS + 1)); note "  [FAIL] $1"; }

check_eq() {   # check_eq <desc> <expected> <actual>
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 [expected=$2 actual=$3]"; fi
}
check_has() {  # check_has <desc> <pattern> <file>
    if grep -q -- "$2" "$3" 2>/dev/null; then ok "$1"; else bad "$1 [missing pattern: $2]"; fi
}
check_not() {  # check_not <desc> <pattern> <file>
    if grep -q -- "$2" "$3" 2>/dev/null; then bad "$1 [unexpected pattern: $2]"; else ok "$1"; fi
}
count_of() {   # count_of <pattern> <file>  -> 匹配行数
    grep -c -- "$1" "$2" 2>/dev/null || true
}
line_no() {    # line_no <file> <n>
    sed -n "$2p" "$1"
}
# THUNK(<个数>, <void?>, <pascal?>, <后缀>) -> "<个数> <后缀>"（去掉一个空格）
thunk_key() {
    printf '%s' "$1" | sed -E 's/^THUNK\(([0-9]+), [0-9]+, [0-9]+, ?([A-Za-z_]*)\)$/\1 \2/'
}

# 上游 thunk_gen.mk 的编号方式：nl -v 0 后去掉行号前的空格
number_lines() { nl -v 0 < "$1" | sed -E 's/^ *//'; }

# 复现 consumer 侧的两条输入流（thunk_gen.mk: thunk_calls.tmp / thunk_asms.tmp）
build_inputs() {
    bash "$PDS" 1 "$DECLS" > "$WORKDIR/calls.filtered" || return 1
    bash "$PDS" 2 "$DECLS" > "$WORKDIR/asms.filtered" || return 1
    number_lines "$WORKDIR/calls.filtered" > "$WORKDIR/thunk_calls.tmp" || return 1
    number_lines "$WORKDIR/asms.filtered" > "$WORKDIR/thunk_asms.tmp" || return 1
    return 0
}

report() {
    note "OHOS_CONSUMER_TESTS mode=$MODE checks=$CHECKS passed=$((CHECKS - FAILS)) failed=$FAILS"
    [ "$FAILS" -eq 0 ]
}

# ─────────────────────────── parse-decls ───────────────────────────
mode_parse_decls() {
    build_inputs || { bad "生成消费者输入流 (parse_decls.sh 1/2)"; report; return; }

    note "-- 筛选器 1（调用侧）：应恰好 4 行、只含调用侧符号、剔除宏定义干扰行"
    check_eq "calls.filtered 行数" "4" "$(wc -l < "$WORKDIR/calls.filtered" | tr -d ' ')"
    check_has "calls.filtered 含 _dos_open" "_dos_open" "$WORKDIR/calls.filtered"
    check_has "calls.filtered 含 _dos_close" "_dos_close" "$WORKDIR/calls.filtered"
    check_has "calls.filtered 含 _dos_putc" "_dos_putc" "$WORKDIR/calls.filtered"
    check_has "calls.filtered 含 _dos_exit" "_dos_exit" "$WORKDIR/calls.filtered"
    check_not "calls.filtered 剔除定义侧符号 _dos_getfree" "_dos_getfree" "$WORKDIR/calls.filtered"
    check_not "calls.filtered 剔除定义侧符号 _dos_ret_ax" "_dos_ret_ax" "$WORKDIR/calls.filtered"
    check_eq "calls.filtered 剔除宏定义干扰行" "0" "$(count_of '^#define' "$WORKDIR/calls.filtered")"

    note "-- 筛选器 2（定义侧）：应恰好 2 行、剔除注释干扰行"
    check_eq "asms.filtered 行数" "2" "$(wc -l < "$WORKDIR/asms.filtered" | tr -d ' ')"
    check_has "asms.filtered 含 _dos_getfree" "_dos_getfree" "$WORKDIR/asms.filtered"
    check_has "asms.filtered 含 _dos_ret_ax" "_dos_ret_ax" "$WORKDIR/asms.filtered"
    check_not "asms.filtered 剔除调用侧符号 _dos_open" "_dos_open" "$WORKDIR/asms.filtered"

    note "-- 编号方式（nl -v 0，与 thunk_gen.mk 一致）：0 起连续"
    check_eq "thunk_calls.tmp 行数" "4" "$(wc -l < "$WORKDIR/thunk_calls.tmp" | tr -d ' ')"
    check_has "thunk_calls.tmp 第 1 条编号为 0" \
        '^0[[:space:]]' "$WORKDIR/thunk_calls.tmp"
    check_has "thunk_calls.tmp 第 4 条编号为 3" \
        '^3[[:space:]]' "$WORKDIR/thunk_calls.tmp"

    note "-- parse_decls.sh 其余分支（脚本完整行为覆盖）"
    bash "$PDS" 3 "$WORKDIR/thunk_calls.tmp" > "$WORKDIR/plt.inc" 2>/dev/null
    check_eq "模式 3 (plt.inc) 行数" "4" "$(wc -l < "$WORKDIR/plt.inc" | tr -d ' ')"
    check_eq "模式 3 第 1 行" "asmcfunc_n _dos_open, 0" "$(line_no "$WORKDIR/plt.inc" 1)"

    bash "$PDS" 4 "$WORKDIR/thunk_asms.tmp" > "$WORKDIR/plt_asmc.h" 2>/dev/null
    check_eq "模式 4 (plt_asmc.h) 第 1 行" "ASMCSYM(_dos_ret_ax, 1)" \
        "$(line_no "$WORKDIR/plt_asmc.h" 1)"

    # 模式 5（pascal 跳转表）：上游 sed 的替换串引用了不存在的第 3 个捕获组，
    # toybox sed 对此直接报错退出（GNU sed 会静默产出空符号名），属平台可移植性
    # 缺陷 —— 由 patches/0001 修正为 \2。此处断言修正后的行为。
    if bash "$PDS" 5 "$WORKDIR/thunk_asms.tmp" > "$WORKDIR/plt_asmp.h" 2>"$WORKDIR/plt_asmp.err"; then
        check_eq "模式 5 (plt_asmp.h) 第 1 行" "ASMPSYM(_DOS_GETFREE, 0)" \
            "$(line_no "$WORKDIR/plt_asmp.h" 1)"
    else
        bad "模式 5 (plt_asmp.h) 在 OHOS 上执行失败: $(cat "$WORKDIR/plt_asmp.err")"
    fi

    bash "$PDS" 6 "$WORKDIR/calls.filtered" > "$WORKDIR/thunk_c1.h" 2>/dev/null
    check_has "模式 6 (thunk_c1.h) 插入 _FUNC()" "_FUNC(_dos_open)" "$WORKDIR/thunk_c1.h"
    bash "$PDS" 7 "$WORKDIR/asms.filtered" > "$WORKDIR/thunk_p1.h" 2>/dev/null
    check_has "模式 7 (thunk_p1.h) 插入 _FUNC()" "_FUNC(_dos_getfree)" "$WORKDIR/thunk_p1.h"

    note "-- mkasmdefs.sh（asm 侧符号宏生成）"
    printf '%s\n' '__ASM(unsigned short, _ds) SEMIC' \
                  '__ASM_FUNC(my_int21_handler) SEMIC' > "$WORKDIR/glob_asm.h"
    sh "$MKADS" "$WORKDIR/glob_asm.h" > "$WORKDIR/glob_asmdefs.h" 2>/dev/null
    check_has "mkasmdefs 生成 __ASYM_L(_ds)" "__ASYM_L(_ds)" "$WORKDIR/glob_asmdefs.h"
    check_has "mkasmdefs 生成 __ASYM(my_int21_handler)" "__ASYM(my_int21_handler)" \
        "$WORKDIR/glob_asmdefs.h"

    report
}

# ─────────────────────────── gen-c ───────────────────────────
mode_gen_c() {
    if [ -z "$OUTFILE" ]; then
        bad "gen-c 模式缺少输出文件参数"
        report
        return
    fi
    build_inputs || { bad "生成消费者输入流 (parse_decls.sh 1/2)"; report; return; }

    if ! "$TGBIN" -a 4 -p 4 < "$WORKDIR/thunk_calls.tmp" > "$OUTFILE"; then
        bad "thunk_gen (thunk_type=0) 执行失败"
        report
        return
    fi
    note "生成 $(wc -l < "$OUTFILE" | tr -d ' ') 行 C 派发表 -> $OUTFILE"

    # 文法语义（src/thunk_gen.y: line -> lnum rdecls fname lb args rb attrs SEMIC）：
    #   case 编号取自输入行编号；返回非 void 用
    #     _DISPATCH(<返回字节数>, _ARG_R(_RET), _RET, <符号>, <参数项>...)
    #   void 用 _DISPATCH_v(<符号>, <参数项>...)；
    #   参数项为 _ARG(偏移, 类型, _SP) / _ARG_PTR(偏移, 类型, _SP)。
    check_eq "case 标签数" "4" "$(count_of '^[[:space:]]*case [0-9]*:' "$OUTFILE")"
    check_eq "派发语句数" "4" "$(count_of '_DISPATCH' "$OUTFILE")"

    check_has "case 0 = _dos_open（void；指针参数在偏移 0，int 在偏移 4）" \
        '_DISPATCH_v(_dos_open, _ARG_PTR(0, const char, _SP), _ARG(4, DWORD, _SP));' "$OUTFILE"
    check_has "case 1 = _dos_close（unsigned int 返回，rlen=4；int 在偏移 0）" \
        '_DISPATCH(4, _ARG_R(UDWORD), _RET, _dos_close, _ARG(0, DWORD, _SP));' "$OUTFILE"
    check_has "case 2 = _dos_putc（void；unsigned char 在偏移 0）" \
        '_DISPATCH_v(_dos_putc, _ARG(0, UBYTE, _SP));' "$OUTFILE"
    check_has "case 3 = _dos_exit（void NORETURN；int 在偏移 0）" \
        '_DISPATCH_v(_dos_exit, _ARG(0, DWORD, _SP));' "$OUTFILE"
    check_not "定义侧符号不得出现在 C 派发表" "_dos_getfree" "$OUTFILE"

    report
}

# ─────────────────────────── asm-templates ───────────────────────────
mode_asm_templates() {
    build_inputs || { bad "生成消费者输入流 (parse_decls.sh 1/2)"; report; return; }

    if ! "$TGBIN" -a 4 -p 4 1 < "$WORKDIR/thunk_asms.tmp" > "$WORKDIR/thunk_type1.txt"; then
        bad "thunk_gen (thunk_type=1) 执行失败"
        report
        return
    fi
    if ! "$TGBIN" -a 4 -p 4 2 < "$WORKDIR/thunk_asms.tmp" > "$WORKDIR/thunk_type2.txt"; then
        bad "thunk_gen (thunk_type=2) 执行失败"
        report
        return
    fi

    note "-- thunk_type=1：m4 模板调用 THUNK(<参数个数>, <void?>, <pascal?>, <后缀>)"
    check_eq "THUNK(...) 条数" "2" "$(count_of '^THUNK(' "$WORKDIR/thunk_type1.txt")"
    check_eq "TG_ABI 声明条数" "1" "$(count_of 'define TG_ABI' "$WORKDIR/thunk_type1.txt")"
    check_has "ASMPASCAL 无参 -> THUNK(0, 0, 1, _P)" \
        '^THUNK(0, 0, 1, _P)$' "$WORKDIR/thunk_type1.txt"
    check_has "ASMFUNC 单参 void -> THUNK(1, 1, 0, _v)" \
        '^THUNK(1, 1, 0, _v)$' "$WORKDIR/thunk_type1.txt"

    note "-- thunk_type=2：C++ 宏调用 _THUNK<参数个数><后缀>(...)"
    check_eq "_THUNK 条数" "2" "$(count_of '^_THUNK' "$WORKDIR/thunk_type2.txt")"
    check_has "生成 _THUNK0_P(" "_THUNK0_P(" "$WORKDIR/thunk_type2.txt"
    check_has "生成 _THUNK1_v(" "_THUNK1_v(" "$WORKDIR/thunk_type2.txt"
    check_has "PASCAL 条目携带符号 _dos_getfree" "_dos_getfree" "$WORKDIR/thunk_type2.txt"
    check_has "ASMFUNC 条目携带符号 _dos_ret_ax" "_dos_ret_ax" "$WORKDIR/thunk_type2.txt"

    note "-- 两阶段一致性：type1 的 THUNK(n, v, p, suffix) 必须与 type2 的 _THUNK<n><suffix> 同名"
    local key n_args suffix want
    while IFS= read -r line; do
        case "$line" in
            THUNK\(*) ;;
            *) continue ;;
        esac
        key="$(thunk_key "$line")"
        n_args="${key%% *}"
        suffix="${key#* }"
        if [ -z "$n_args" ] || [ "$key" = "$line" ]; then
            bad "无法解析 THUNK 行: $line"
            continue
        fi
        want="_THUNK${n_args}${suffix}("
        check_has "type2 含 $want" "$want" "$WORKDIR/thunk_type2.txt"
    done < "$WORKDIR/thunk_type1.txt"

    report
}

# ─────────────────────────── m4-pipeline ───────────────────────────
mode_m4_pipeline() {
    if ! command -v autom4te >/dev/null 2>&1; then
        note "SKIP: m4sugar 阶段需要 autoconf 的 autom4te（下游消费者工具），当前平台未提供"
        exit 77
    fi
    build_inputs || { bad "生成消费者输入流 (parse_decls.sh 1/2)"; report; return; }

    # 等价于 thunk_gen.mk 的：($(TG) $(TFLAGS) 1 <$< | $(TGS) $(TGM4) >$@_)
    # （tg_m4 以 stdin 为输入，故拆成两步以便保留中间产物）
    if ! "$TGBIN" -a 4 -p 4 1 < "$WORKDIR/thunk_asms.tmp" \
            > "$WORKDIR/thunk_type1_m4.txt"; then
        bad "thunk_gen (thunk_type=1) 执行失败"
        report
        return
    fi
    if ! bash "$TGS" "$TGM4" < "$WORKDIR/thunk_type1_m4.txt" \
            > "$WORKDIR/thunk_asms_m4.h"; then
        bad "m4sugar 管线（tg_m4 + thunks.m4）执行失败"
        report
        return
    fi
    note "m4 管线输出 $(wc -l < "$WORKDIR/thunk_asms_m4.h" | tr -d ' ') 行 -> thunk_asms_m4.h"

    check_has "m4sugar 展开 sp_num(TG_ABI)" '^#define TG_ABI 3' "$WORKDIR/thunk_asms_m4.h"
    check_has "m4 输出含 __CALL 派发点" "__CALL" "$WORKDIR/thunk_asms_m4.h"

    note "-- 交叉一致性：type1 的每条 THUNK 都必须在 m4 输出里展开成同名模板"
    local key n_args suffix want
    while IFS= read -r line; do
        case "$line" in
            THUNK\(*) ;;
            *) continue ;;
        esac
        key="$(thunk_key "$line")"
        n_args="${key%% *}"
        suffix="${key#* }"
        want="#define _THUNK${n_args}${suffix}("
        check_has "m4 输出含 $want" "$want" "$WORKDIR/thunk_asms_m4.h"
    done < "$WORKDIR/thunk_type1_m4.txt"

    report
}

case "$MODE" in
    parse-decls)   mode_parse_decls ;;
    gen-c)         mode_gen_c ;;
    asm-templates) mode_asm_templates ;;
    m4-pipeline)   mode_m4_pipeline ;;
    *)
        echo "unknown mode: $MODE" >&2
        exit 2
        ;;
esac
