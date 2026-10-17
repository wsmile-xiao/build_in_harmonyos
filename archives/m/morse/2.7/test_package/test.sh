#!/bin/bash
# test.sh — morse 2.7 (Morse Classic) 真实 CLI 功能测试
# 由 test_package/conanfile.py 的 test() 调用（bash 在 PATH 中，
# LD_PRELOAD 指向调用方编译好的 console shim）。
#
# 依赖：安装后的真实 morse / QSO 二进制已在 $PATH 中
# （conan run_environment 将 package 的 bin/ 加入 PATH）。
#
# 说明：morse 的音频输出走 /dev/console（PC 喇叭）。OHOS 上没有
# PC 喇叭且 /dev/console 无写权限，这里用与配方 build() 相同的
# console shim（LD_PRELOAD，仅重定向 /dev/console 的 open() 到
# /dev/null）让真实 CLI 真正执行；解码、SIGALRM 计时、stdout
# 输出全部为真实路径。shim 由 test_package/conanfile.py 编译于
# 临时目录，绝不进入安装产物。
#
# 所有断言均从上游源码（morse.c / QSO.c）语义实测导出（见
# notes.md 的行为表），为精确输出断言；无 || true / ignore_errors /
# 无条件 OK / 只检查不崩溃。

set -u
export LC_ALL=C

PASS=0
FAIL=0
TOTAL=0
FAILURES=()

t() { # t <name> <expected_exit> <actual_exit> — exit-code assertion
    TOTAL=$((TOTAL + 1))
    if [ "$3" = "$2" ]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAILURES+=("  $1: exit $3 != $2")
    fi
}

check() { # check <name> <condition-rc> <detail-on-fail>
    TOTAL=$((TOTAL + 1))
    if [ "$2" = "0" ]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAILURES+=("  $1: $3")
    fi
}

TMPD=$(mktemp -d) || exit 2
trap 'rm -rf "$TMPD"' EXIT

main() {
    # ── 0. CLI 在 PATH 中（真实安装后的二进制）──
    command -v morse >/dev/null 2>&1
    t "morse-in-PATH" 0 $?
    command -v QSO >/dev/null 2>&1
    t "QSO-in-PATH" 0 $?

    # ── 1. 文本→Morse 精确转换（-m：屏幕点划；-e：无错误音）──
    # 上游语义（实测）：每词输出一行，词内字母以空格分隔，词尾
    # 空格保留，结尾一个空行。用文件比对保留精确字节（含尾随
    # 空格与换行），不受 $(...) 剥尾换行影响。
    printf 'SOS' | morse -w 24 -m -e >"$TMPD/o1" 2>"$TMPD/e1"; ec=$?
    t "txt2morse-SOS-exit" 0 $ec
    printf '... --- ... \n\n' >"$TMPD/want1"
    cmp -s "$TMPD/o1" "$TMPD/want1"
    check "txt2morse-SOS-exact" $? "got $(od -c "$TMPD/o1" | head -2)"
    [ ! -s "$TMPD/e1" ]
    check "txt2morse-SOS-clean-stderr" $? "stderr: $(cat "$TMPD/e1")"

    # 多字符输入：两个词 → 两行
    printf 'SOS PARIS' | morse -w 24 -m -e >"$TMPD/o2" 2>/dev/null; ec=$?
    t "txt2morse-multi-exit" 0 $ec
    printf '... --- ... \n.--. .- .-. .. ... \n\n' >"$TMPD/want2"
    cmp -s "$TMPD/o2" "$TMPD/want2"
    check "txt2morse-multi-exact" $? "got $(od -c "$TMPD/o2" | head -4)"

    # 数字
    printf '123' | morse -w 24 -m -e >"$TMPD/o3" 2>/dev/null; ec=$?
    t "txt2morse-digits-exit" 0 $ec
    printf '.---- ..--- ...-- \n\n' >"$TMPD/want3"
    cmp -s "$TMPD/o3" "$TMPD/want3"
    check "txt2morse-digits-exact" $? "got $(od -c "$TMPD/o3" | head -3)"

    # 长句（上游 test_input 首句：7 个空格分隔词（quartz. 的句号
    # 并入词内点划 .-.-.-）→ 7 行点划 + 末空行）
    printf 'Jackdaws love my big sphinx of quartz.' | morse -w 24 -m -e >"$TMPD/o4" 2>/dev/null; ec=$?
    t "txt2morse-sentence-exit" 0 $ec
    nlines=$(grep -c . "$TMPD/o4")
    [ "$nlines" = "7" ]
    check "txt2morse-sentence-7-lines" $? "lines=$nlines out=$(cat "$TMPD/o4")"
    # 首词 Jackdaws 的精确点划
    first=$(head -1 "$TMPD/o4")
    [ "$first" = ".--- .- -.-. -.- -.. .- .-- ... " ]
    check "txt2morse-sentence-first-word" $? "got '$first'"

    # ── 2. 字母同步输出（-l：字母与点划同行）──
    printf 'SOS' | morse -w 24 -l -m -e >"$TMPD/o5" 2>/dev/null; ec=$?
    t "letters-SOS-exit" 0 $ec
    printf 'S... O--- S... \n\n' >"$TMPD/want5"
    cmp -s "$TMPD/o5" "$TMPD/want5"
    check "letters-SOS-exact" $? "got $(od -c "$TMPD/o5" | head -3)"

    # ── 3. 负向：-C 空字符集（上游 morse.c:600 的报错路径）──
    out=$(morse -w 24 -C '%%%' -m -e </dev/null 2>"$TMPD/e3"); ec=$?
    t "charset-empty-exit" 1 $ec
    [ "$out" = "" ]
    check "charset-empty-no-stdout" $? "got '$out'"
    grep -q 'Error: -C charset selects no valid characters.' "$TMPD/e3"
    check "charset-empty-stderr-msg" $? "stderr: $(cat "$TMPD/e3")"

    # 负向：未识别选项（getopt → stderr 自提示 + exit 1）
    out=$(morse -Z </dev/null 2>"$TMPD/e4"); ec=$?
    t "unknown-option-exit" 1 $ec
    grep -q 'unrecognized option: Z' "$TMPD/e4"
    check "unknown-option-msg" $? "stderr: $(cat "$TMPD/e4")"
    grep -q 'Type "morse" without arguments to get self-doc' "$TMPD/e4"
    check "unknown-option-self-doc" $? "stderr: $(cat "$TMPD/e4")"

    # ── 4. QSO 报文生成器（结构断言；随机文本但结构固定）──
    qso=$(QSO 2>/dev/null); ec=$?
    t "qso-exit" 0 $ec
    lines=$(printf '%s\n' "$qso" | grep -c .)
    [ "$lines" -ge 8 ]
    check "qso-min-lines" $? "lines=$lines"
    # 首行 = 尾行：呼号 de 呼号（可含 /数字 后缀，如 WH6UR/5）
    head=$(printf '%s\n' "$qso" | head -1)
    tail=$(printf '%s\n' "$qso" | grep -v '^$' | tail -1)
    printf '%s' "$head" | grep -Eq '^[A-Z0-9]+(/[0-9]+)? de [A-Z0-9]+(/[0-9]+)?$'
    check "qso-header-callsign" $? "head='$head'"
    [ "$head" = "$tail" ]
    check "qso-tail-echoes-head" $? "head='$head' tail='$tail'"
    # RST 信号报告行（上游 PutRST：8 种随机格式 × 分隔符 = / ,
    # 如 "UR RST 599=599." / "Your signal is RST 599/599."
    # / "UR signal is RST 126,126."）
    printf '%s' "$qso" | grep -Eq 'RST( is)? [0-9]{3}[=/,][0-9]{3}\.'
    check "qso-rst-line" $? "no RST line"
    # CW 交换结束标记 +% 行
    printf '%s' "$qso" | grep -q '^+ *%$'
    check "qso-plus-percent" $? "no '+%' line"

    # ── 5. 无参数非 tty：上游语义（argc==1 且非终端）静默退出 0 ──
    out=$(morse </dev/null 2>"$TMPD/e5"); ec=$?
    t "noargs-nontty-exit" 0 $ec
    [ -z "$out" ] && [ ! -s "$TMPD/e5" ]
    check "noargs-nontty-silent" $? "out='$out' err='$(cat "$TMPD/e5")'"
}

main
rc=$?

echo "────────────────────────────"
echo "test.sh: TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL SKIP=0"
if [ "$FAIL" -gt 0 ]; then
    echo "Failures:"
    printf '%s\n' "${FAILURES[@]}"
    exit 1
fi
exit 0
