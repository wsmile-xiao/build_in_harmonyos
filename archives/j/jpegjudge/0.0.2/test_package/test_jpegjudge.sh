#!/data/service/hnp/bin/bash
# test_package/test_jpegjudge.sh — jpegjudge 消费者行为测试（真运行 + 真断言）
#
# 用法: bash test_jpegjudge.sh <judge 可执行文件绝对路径> <夹具目录>
#
# 夹具由本 test_package 的 build() 落盘：4 个用 IJG libjpeg 编码器
# （jpeg_set_quality / JCS_GRAYSCALE）真实生成的 JPEG；
# 生成程序与逐文件 sha256 记在版本级 notes.md「消费者测试夹具」一节。
#
# 断言里的数字（424 / 293 / 0 / 1000 / 截断件 < 424）全部来自本机构建产物的
# 实测值，不是推算：见 reports/consumer-probe.log 与 notes.md。
#
# 覆盖面：选项面与退出码契约（长选项 -version/-help 为本次适配补丁）、
# 真实 JPEG 判定值的确定性与区分度、纯色/不足块宽度的边界、
# -b 输出形态、stdin 读入、非 JPEG、缺失文件、好坏混合、截断文件。
set -u

BIN="$1"
FIX="$2"
pass=0
fail=0
bad_list=""

if [ ! -x "$BIN" ]; then
  echo "FATAL: 被测二进制不可执行: $BIN"
  exit 70
fi

ok()  { pass=$((pass + 1)); echo "PASS  $1"; }
bad() { fail=$((fail + 1)); bad_list="${bad_list}
  - $1"; echo "FAIL  $1"; }

# eq <用例名> <期望> <实际>
eq() {
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 [期望=<$2> 实际=<$3>]"; fi
}

# has <用例名> <子串> <文本>
has() {
  case "$3" in
    *"$2"*) ok "$1" ;;
    *) bad "$1 [未包含<$2>，实际=<$3>]" ;;
  esac
}

# num <judge 输出> —— 判定行格式是 "%s: %3d"；取最后一条以「…: 数字」结尾的行。
# 不能直接对整个输出做替换：坏文件场景下 judge 会先输出告警行（如截断件的
# "Premature end of JPEG file" / "jpeg read error"），逐行替换会把告警一起带出来。
num() {
  printf '%s\n' "$1" \
    | sed -n 's/.*:[[:space:]]*\([0-9][0-9]*\)[[:space:]]*$/\1/p' \
    | tail -1
}

cd "$FIX" || exit 71

# 真实输入准备：截断件与非 JPEG 件现场派生，不把二进制垃圾留在仓库里
head -c 400 hi_noise.jpg > case_trunc.jpg
printf 'NOT A JPEG FILE AT ALL, JUST PLAIN TEXT 1234\n' > case_notjpeg.jpg

# ── 组 A：选项面与退出码契约 ──────────────────────────────────
OUT="$("$BIN" --version 2>&1)"; RC=$?
eq "A1 --version 退出码 0" "0" "$RC"
eq "A2 --version 输出 judge version 0.0.2" "judge version 0.0.2" "$OUT"

OUT="$("$BIN" --help 2>&1)"; RC=$?
eq "A3 --help 退出码 0" "0" "$RC"
has "A4 --help 输出用法行" "Usage:" "$OUT"

OUT="$("$BIN" -v 2>&1)"; RC=$?
eq "A5 上游短选项 -v 退出码 0" "0" "$RC"
eq "A6 上游短选项 -v 输出未回归" "judge version 0.0.2" "$OUT"

"$BIN" >/dev/null 2>&1; RC=$?
eq "A7 无参数退出码 2（用法错误）" "2" "$RC"

"$BIN" -Z >/dev/null 2>&1; RC=$?
eq "A8 未知选项 -Z 退出码 2" "2" "$RC"

"$BIN" -h >/dev/null 2>&1; RC=$?
eq "A9 上游短选项 -h 退出码 0" "0" "$RC"

# ── 组 B：真实 JPEG 的判定行为 ────────────────────────────────
OUT_HI="$("$BIN" hi_noise.jpg 2>&1)"; RC=$?
eq "B1 高质量件退出码 0" "0" "$RC"
eq "B2 高质量件输出 = 文件名 + 实测值 424" "hi_noise.jpg: 424" "$OUT_HI"

OUT_HI2="$("$BIN" hi_noise.jpg 2>&1)"
eq "B3 同一文件重复判定输出逐字一致（判重确定性）" "$OUT_HI" "$OUT_HI2"

cp hi_noise.jpg hi_copy.jpg
OUT_CP="$("$BIN" hi_copy.jpg 2>&1)"
eq "B4 内容相同的两份文件指示值相同（424）" "424" "$(num "$OUT_CP")"

OUT_LO="$("$BIN" lo_noise.jpg 2>&1)"; RC=$?
eq "B5 低质量件退出码 0" "0" "$RC"
eq "B6 低质量件指示值实测 293" "293" "$(num "$OUT_LO")"

V_HI="$(num "$OUT_HI")"
V_LO="$(num "$OUT_LO")"
if [ "$V_HI" -gt "$V_LO" ]; then
  ok "B7 同一图像、编码质量不同 ⇒ 指示值可区分（$V_HI > $V_LO）"
else
  bad "B7 hi 未大于 lo（hi=$V_HI lo=$V_LO）"
fi

OUT_FLAT="$("$BIN" flat.jpg 2>&1)"; RC=$?
eq "B8 纯色图指示值落在下界 0" "0" "$(num "$OUT_FLAT")"

"$BIN" tiny_4x4.jpg >/dev/null 2>&1; RC=$?
eq "B9 宽度不足一个 8x8 块时不崩溃（AArch64 整数除 0 不陷入，退出码 0）" "0" "$RC"
OUT_TINY="$("$BIN" tiny_4x4.jpg 2>&1)"
eq "B10 宽度不足一个 8x8 块时实测指示值 1000（上游除零边界，notes.md 记为已知限制）" "1000" "$(num "$OUT_TINY")"

# ── 组 C：-b 输出形态与多文件、stdin ──────────────────────────
OUT_B="$("$BIN" -b hi_noise.jpg lo_noise.jpg 2>&1)"; RC=$?
eq "C1 -b 退出码 0" "0" "$RC"
LINES="$(printf '%s\n' "$OUT_B" | wc -l | tr -d ' ')"
eq "C2 -b 两个文件输出两行" "2" "$LINES"
BARE="$(printf '%s\n' "$OUT_B" | grep -cE '^[[:space:]]*[0-9]+$' | tr -d ' ')"
eq "C3 -b 每行只有数字（文件名被抑制）" "2" "$BARE"

"$BIN" - < hi_noise.jpg > stdin_case.out 2>&1; RC=$?
eq "C4 用 - 从 stdin 读取退出码 0" "0" "$RC"
eq "C5 stdin 与文件方式的指示值一致" "424" "$(num "$(cat stdin_case.out)")"

OUT_MULTI="$("$BIN" hi_noise.jpg lo_noise.jpg flat.jpg 2>&1)"; RC=$?
eq "C6 三文件退出码 0" "0" "$RC"
eq "C7 三文件输出三行" "3" "$(printf '%s\n' "$OUT_MULTI" | wc -l | tr -d ' ')"
has "C8 三文件输出含各自的指示值行" "flat.jpg:   0" "$OUT_MULTI"

# ── 组 D：坏输入 ──────────────────────────────────────────────
ERR="$("$BIN" case_notjpeg.jpg 2>&1 >/dev/null)"; RC=$?
eq "D1 非 JPEG 输入退出码 1" "1" "$RC"
has "D2 非 JPEG 输入报 Not a JPEG file" "Not a JPEG file" "$ERR"

ERR="$("$BIN" no_such_file.jpg 2>&1 >/dev/null)"; RC=$?
eq "D3 不存在的文件退出码 1" "1" "$RC"
has "D4 不存在的文件报 No such file or directory" "No such file or directory" "$ERR"

OUT_MIX="$("$BIN" hi_noise.jpg no_such_file.jpg 2>/dev/null)"; RC=$?
eq "D5 好+坏混合时整体退出码 1" "1" "$RC"
has "D6 好+坏混合时好文件仍被判定（不被单个坏输入中断）" "hi_noise.jpg: 424" "$OUT_MIX"

OUT_TR="$("$BIN" case_trunc.jpg 2>&1)"; RC=$?
eq "D7 截断 JPEG 仍完成判定（退出码 0）" "0" "$RC"
has "D8 截断 JPEG 报告 jpeg read error" "jpeg read error" "$OUT_TR"
V_TR="$(num "$OUT_TR")"
if [ "$V_TR" -lt "$V_HI" ]; then
  ok "D9 截断件指示值低于完整件（$V_TR < $V_HI）"
else
  bad "D9 截断件指示值未低于完整件（$V_TR vs $V_HI）"
fi

rm -f case_trunc.jpg case_notjpeg.jpg hi_copy.jpg stdin_case.out

echo "SUMMARY pass=$pass fail=$fail"
if [ "$fail" -gt 0 ]; then
  echo "失败用例:$bad_list"
  exit 1
fi
exit 0
