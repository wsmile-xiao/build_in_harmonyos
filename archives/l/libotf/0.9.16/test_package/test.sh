#!/bin/sh
# test.sh — libotf/0.9.16 单元测试（1 例）+ 集成测试（4 例）
#
# 用法（由 test_package/conanfile.py 以 bash 调用，cwd = 测试构建目录）：
#   test.sh <conan-package-folder> <consumer-executable>
#
# 用例（逐条输出 ok/FAIL，独立统计；内部多项断言不冒充独立用例）：
#   U1  单元测试：./test_consumer 消费者 API 测试（链接安装后的 libotf，
#       与 freetype 逐字符交叉验证 cmap）
#   I1  集成测试：otfdump  端到端（真实 OTF 字体 → OTF 表转储）
#   I2  集成测试：otflist  端到端（字体目录扫描与枚举）
#   I3  集成测试：otftobdf 端到端（OTF → BDF 字体流）
#   I4  集成测试：损坏字体负向（截断字体 → 报错退出且未被信号杀死）
set -u

if [ $# -lt 2 ]; then
	echo "usage: $0 <conan-package-folder> <consumer-executable>" >&2
	exit 2
fi

PKG="$1"
CONSUMER="$2"
BIN="$PKG/bin"

case "$CONSUMER" in
	/*) ;;
	*) CONSUMER="$(pwd)/$CONSUMER" ;;
esac

# 临时目录：/tmp 在本平台可能只读（E002），按 TMPDIR → $HOME/tmp → 当前目录回退
WORK=""
for d in "${TMPDIR:-}" "$HOME/tmp" "$(pwd)"; do
	[ -n "$d" ] || continue
	if mkdir -p "$d/.libotf-test-$$" 2>/dev/null; then
		WORK="$d/.libotf-test-$$"
		break
	fi
done
[ -n "$WORK" ] || { echo "TEST FAIL: 无可写临时目录" >&2; exit 1; }
trap 'rm -rf "$WORK"' EXIT

FAIL=0
CASES=0
ok()  { CASES=$((CASES + 1)); echo "ok: $*"; }
bad() { CASES=$((CASES + 1)); FAIL=$((FAIL + 1)); echo "TEST FAIL: $*" >&2; }

for t in otfdump otflist otftobdf; do
	[ -x "$BIN/$t" ] || { echo "TEST FAIL: 缺少可执行文件 $BIN/$t" >&2; exit 1; }
done

# ── 确定性输入：从系统字体中挑选带 OTF 布局表者 ──
CJK_FONT=""
for f in /system/fonts/HarmonyOS_Sans_SC.ttf /system/fonts/HarmonyOS_Sans.ttf \
         /system/fonts/FZHeiT-SC-Regular.ttf /system/fonts/NotoSansCJK-Regular.ttc; do
	if [ -f "$f" ] && "$BIN/otfdump" "$f" 2>/dev/null | grep -qE 'GSUB|GPOS'; then
		CJK_FONT="$f"
		break
	fi
done
if [ -z "$CJK_FONT" ]; then
	echo "TEST FAIL: 未找到含 OTF 布局表（GSUB/GPOS）的系统字体" >&2
	exit 1
fi

# 小体积字体用于 otftobdf（CJK 字体枚举 cmap 较慢，仅作回退）
SMALL_FONT=""
for f in /system/fonts/FTChariSans.ttf /system/fonts/FTAeroSans-Regular.ttf \
         /system/fonts/DejaVuMathTeXGyre.ttf; do
	if [ -f "$f" ]; then
		SMALL_FONT="$f"
		break
	fi
done
[ -n "$SMALL_FONT" ] || SMALL_FONT="$CJK_FONT"
echo "info: 布局表字体=$CJK_FONT 小字体=$SMALL_FONT"

# ── U1 单元测试：消费者 API 测试 ──
if [ -x "$CONSUMER" ]; then
	OUT="$("$CONSUMER" "$CJK_FONT" 2>&1)"
	RC=$?
	NOK=$(echo "$OUT" | grep -c '^ok:')
	if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'ALL TESTS PASSED'; then
		ok "U1 消费者 API 测试（${NOK} 项断言全部通过）"
	else
		bad "U1 消费者 API 测试 rc=$RC: $(echo "$OUT" | grep '^FAIL' | head -3 | tr '\n' ' ')"
	fi
else
	bad "U1 消费者可执行文件不可用: $CONSUMER"
fi

# ── I1 集成测试：otfdump ──
"$BIN/otfdump" "$CJK_FONT" > "$WORK/i1.out" 2> "$WORK/i1.err"
RC=$?
LINES=$(wc -l < "$WORK/i1.out")
if [ "$RC" -eq 0 ] && [ "$LINES" -ge 100 ] && grep -q 'GSUB' "$WORK/i1.out"; then
	ok "I1 otfdump 端到端（rc=0, ${LINES} 行转储, 含 GSUB 表）"
else
	bad "I1 otfdump rc=$RC lines=$LINES err=$(head -c 150 "$WORK/i1.err")"
fi

# ── I2 集成测试：otflist ──
DIR=$(dirname "$CJK_FONT")
BASE=$(basename "$CJK_FONT")
"$BIN/otflist" "$DIR" > "$WORK/i2.out" 2>&1
RC=$?
if [ "$RC" -eq 0 ] && grep -q "$BASE" "$WORK/i2.out"; then
	ok "I2 otflist 端到端（rc=0, $(wc -l < "$WORK/i2.out") 行, 列出 $BASE）"
else
	bad "I2 otflist rc=$RC out=$(head -c 150 "$WORK/i2.out")"
fi

# ── I3 集成测试：otftobdf ──
"$BIN/otftobdf" "$SMALL_FONT" > "$WORK/i3.bdf" 2> "$WORK/i3.err"
RC=$?
CHARS=$(sed -n 's/^CHARS \([0-9][0-9]*\)$/\1/p' "$WORK/i3.bdf" | head -1)
if [ "$RC" -eq 0 ] && grep -q '^STARTFONT' "$WORK/i3.bdf" \
   && grep -q '^ENDFONT' "$WORK/i3.bdf" \
   && [ -n "${CHARS:-}" ] && [ "$CHARS" -ge 100 ]; then
	ok "I3 otftobdf 端到端（rc=0, BDF $(wc -c < "$WORK/i3.bdf") 字节, CHARS=$CHARS）"
else
	bad "I3 otftobdf rc=$RC CHARS=${CHARS:-无} err=$(head -c 150 "$WORK/i3.err")"
fi

# ── I4 集成测试：损坏字体负向 ──
head -c 4096 "$CJK_FONT" > "$WORK/corrupt.otf"
"$BIN/otfdump" "$WORK/corrupt.otf" > "$WORK/i4.out" 2> "$WORK/i4.err"
RC=$?
if [ "$RC" -ne 0 ] && [ "$RC" -lt 128 ] && grep -q 'OTF-Error' "$WORK/i4.err"; then
	ok "I4 损坏字体负向（rc=$RC, 报 OTF-Error, 未被信号杀死）"
else
	bad "I4 损坏字体负向 rc=$RC err=$(head -c 150 "$WORK/i4.err")"
fi

echo "== test.sh: 用例 ${CASES} 个, 失败 ${FAIL} 个 =="
[ "$FAIL" -eq 0 ] || exit 1
echo "ALL TESTS PASSED (test.sh)"
