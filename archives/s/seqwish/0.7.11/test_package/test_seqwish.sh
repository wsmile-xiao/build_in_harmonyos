#!/usr/bin/env bash
# seqwish 消费者用例（conan test_package）
# 用法: sh test_seqwish.sh <package bin dir> <package folder>
# 断言两类：①交付物与上游语义（真跑二进制构图）；②[OHOS] 平台属性。
set -u

BINDIR="${1:?bindir required}"
PKG="${2:-}"
BIN="$BINDIR/seqwish"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "PASS: $1"; }
no()  { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }

# chk <name> <actual> <expected>
chk() {
    if [ "$2" = "$3" ]; then ok "$1"; else no "$1 (expected [$3], got [$2])"; fi
}
# grepq <name> <file> <pattern>
grepq() {
    if grep -q -- "$3" "$2" 2>/dev/null; then ok "$1"; else no "$1 (pattern [$3] not found in $2)"; fi
}

WORK="$(mktemp -d "${TMPDIR:-.}/seqwish-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# ---------------------------------------------------------------- 交付物
chk "bin/seqwish 存在且可执行" "$([ -x "$BIN" ] && echo yes || echo no)" "yes"
chk "bin/seqwish 非空" "$([ -s "$BIN" ] && echo yes || echo no)" "yes"
chk "包内不夹带静态/动态库产物" \
    "$(find "$PKG" -type f \( -name '*.a' -o -name '*.so*' \) | wc -l | tr -d ' ')" "0"
chk "licenses/LICENSE 随包交付" \
    "$([ -s "$PKG/licenses/LICENSE" ] && echo yes || echo no)" "yes"

# ---------------------------------------------------------------- 上游语义
"$BIN" -h > help.txt 2>&1
chk "seqwish -h 退出码 0" "$?" "0"
grepq "帮助文本含上游标语" help.txt "seqwish: a variation graph inducer"

# 合成最小真实用例：一条序列对自身的 16M 比对
printf '>s1\nACGTACGTACGTACGT\n' > s.fa
printf 's1\t16\t0\t16\t+\ts1\t16\t0\t16\t16\t16\t255\tcg:Z:16M\n' > a.paf

"$BIN" -s s.fa -p a.paf -g out.gfa > seqwish.log 2>&1
chk "真实图构建退出码 0" "$?" "0"
chk "GFA 行数（H/S/P）" "$(wc -l < out.gfa | tr -d ' ')" "3"
grepq "GFA 头部版本标记" out.gfa "VN:Z:1.0"
grepq "GFA 序列段与输入一致" out.gfa "ACGTACGTACGTACGT"
grepq "GFA 路径段记录输入序列" out.gfa "P	s1	1+"

"$BIN" -s s.fa -p a.paf -g out2.gfa > /dev/null 2>&1
chk "同输入两次输出字节一致（确定性）" \
    "$(md5sum out.gfa | cut -d' ' -f1)" "$(md5sum out2.gfa | cut -d' ' -f1)"

# 无比对记录的 PAF：仍须产出合法最小图且不崩
: > empty.paf
"$BIN" -s s.fa -p empty.paf -g empty.gfa > /dev/null 2>&1
chk "空 PAF 退出码 0（不崩溃）" "$?" "0"
grepq "空 PAF 仍产出 GFA 头部" empty.gfa "VN:Z:1.0"

# gzip 形态输入（上游测试数据的形态）
if command -v gzip > /dev/null 2>&1; then
    gzip -c s.fa > s.fa.gz
    gzip -c a.paf > a.paf.gz
    "$BIN" -s s.fa.gz -p a.paf.gz -g gz.gfa > /dev/null 2>&1
    chk "gzip 形态输入退出码 0" "$?" "0"
    chk "gzip 与明文输入结果一致" \
        "$(md5sum gz.gfa | cut -d' ' -f1)" "$(md5sum out.gfa | cut -d' ' -f1)"
fi

# 负向对照：未知选项必须失败
if "$BIN" --definitely-not-an-option > /dev/null 2>&1; then
    no "未知选项应失败"
else
    ok "未知选项退出码非 0"
fi

# ---------------------------------------------------------------- [OHOS]
if grep -q "ld-musl" /proc/self/maps 2>/dev/null; then
    ok "[OHOS] 宿主 C 库为 musl（/proc/self/maps 含 ld-musl）"
else
    no "[OHOS] 宿主 C 库非 musl"
fi

ELFHDR="$(od -An -tx1 -N20 "$BIN" | tr -s ' \n' ' ')"
case "$ELFHDR" in
    *"7f 45 4c 46"*) ok "[OHOS] 产物为 ELF" ;;
    *) no "[OHOS] 产物非 ELF" ;;
esac
case "$ELFHDR" in
    *"02 01 01 00"*) ok "[OHOS] 产物为 64 位小端 ELF" ;;
    *) no "[OHOS] 产物非 64 位小端 ELF" ;;
esac
case "$ELFHDR" in
    *"03 00 b7 00"*) ok "[OHOS] 产物为 AArch64 PIE（e_type=ET_DYN, e_machine=0xb7）" ;;
    *) no "[OHOS] 产物非 AArch64 PIE" ;;
esac

if grep -aq "libc\.so\.6" "$BIN"; then
    no "[OHOS] 产物不引用 glibc（发现 libc.so.6）"
else
    ok "[OHOS] 产物不引用 glibc（无 libc.so.6）"
fi
if grep -aq "libc\.so" "$BIN"; then
    ok "[OHOS] 产物按 musl 命名引用 libc.so"
else
    no "[OHOS] 产物未引用 musl 命名 libc.so"
fi
if grep -aq "libc++_shared\.so" "$BIN"; then
    ok "[OHOS] 交付物链接 OHOS libc++ 运行时"
else
    no "[OHOS] 交付物未链接 OHOS libc++ 运行时"
fi
if grep -aq "libomp\.so" "$BIN"; then
    ok "[OHOS] 交付物链接平台 OpenMP 运行时 libomp.so"
else
    no "[OHOS] 交付物未链接平台 OpenMP 运行时"
fi

echo "----------------------------------------"
echo "PASS: $PASS FAIL: $FAIL (total $((PASS + FAIL)))"
[ "$FAIL" -eq 0 ]
