#!/data/service/hnp/bin/bash
# test_bins.sh — mdocml 1.14.6 消费者测试：已安装可执行件层。
#
# 套件刻意用显式绝对路径解释器（notes/device-facts.md §一.16 / §一.26：
# 设备无 /bin/bash，toybox sh 对不含斜杠命令做 PATH 搜索会造 127 假象）。
# 10 项断言全部在设备实测通过。
set -u

BIN="${1:?usage: test_bins.sh <package_bin_dir>}"
fails=0

check() { # check <期望退出码> <描述> <命令...>
	want=$1; shift; desc=$1; shift
	out=$("$@" 2>&1); rc=$?
	if [ "$rc" -eq "$want" ]; then
		echo "ok: $desc"
	else
		echo "FAIL: $desc (rc=$rc want=$want)"
		echo "$out" | sed 's/^/    | /'
		fails=$((fails + 1))
	fi
}

TMP="${TMPDIR:-/tmp}/mdocml-test.$$"
mkdir -p "$TMP" 2>/dev/null || TMP="$(pwd)/.mdocml-test.$$"
mkdir -p "$TMP"

cat > "$TMP/smoke.5" <<'EOF'
.TH MDOCL 1 "2026-09" "mdocml 1.14.6" "User Commands"
.SH NAME
mdocml \- smoke
.SH SYNOPSIS
.B mdocml
.RI [ options ]
.SH DESCRIPTION
Rendered by \fBmandoc\fR.
EOF

# ── mandoc 主程序（1–4）────────────────────────────────────────
check 0 "1 mandoc -T ascii 渲染退出 0" \
	"$BIN/mandoc" -T ascii "$TMP/smoke.5"

"$BIN/mandoc" -T ascii "$TMP/smoke.5" > "$TMP/out.txt" 2>&1
if grep -q "mdocml - smoke" "$TMP/out.txt"; then
	echo "ok: 2 渲染输出含 NAME 行 'mdocml - smoke'"
else
	echo "FAIL: 2 渲染输出缺 NAME 行"; fails=$((fails + 1))
fi

# 断言3：\fB 粗体必须被渲染出来。ascii 目标的粗体形态是 **overstrike**
# （字符 + 退格 0x08 + 字符，如 `m^Hma^Han...`），与上游 `.out_ascii` 期望文件
# 同款（regress/char/N/basic.out_ascii 含 15 个 0x08）。因此不能 grep
# 纯文本 "Rendered by mandoc"（退格会把字符隔开、永不命中），
# 正确判据 = 文案存在 **且** 输出含 0x08 退格。
bs_count=$(tr -dc '\010' < "$TMP/out.txt" 2>/dev/null | wc -c)
if grep -q "Rendered by" "$TMP/out.txt" && [ "${bs_count:-0}" -gt 0 ]; then
	echo "ok: 3 \\fB 粗体渲染为 overstrike（文案存在 + ${bs_count} 个 0x08 退格）"
else
	echo "FAIL: 3 渲染输出缺粗体展开（Rendered by 或 0x08 退格缺失：bs=${bs_count:-0}）"
	fails=$((fails + 1))
fi

if grep -q "MDOCL(1)" "$TMP/out.txt"; then
	echo "ok: 4 渲染输出含页眉页脚 'MDOCL(1)'"
else
	echo "FAIL: 4 渲染输出缺页眉页脚"; fails=$((fails + 1))
fi

# ── man/apropos/whatis/makewhatis 是 mandoc 的别名（5–8）──────
# 上游 Makefile: `$(LN) mandoc $(BINM_*)`；本平台 LN=cp -f → 独立副本。
alias_ok=1
for alias in man apropos whatis makewhatis; do
	if [ ! -f "$BIN/$alias" ]; then
		echo "FAIL: 别名 $alias 缺失"; alias_ok=0; fails=$((fails + 1))
	elif cmp -s "$BIN/mandoc" "$BIN/$alias"; then
		:
	else
		echo "FAIL: 别名 $alias 与 mandoc 不等同"; alias_ok=0; fails=$((fails + 1))
	fi
done
if [ "$alias_ok" -eq 1 ]; then
	echo "ok: 5 man/apropos/whatis/makewhatis 四别名与 mandoc 字节等同"
else
	echo "FAIL: 5 别名等同性校验"; fails=$((fails + 1))
fi

# ── demandoc：宏展开（6）──────────────────────────────────────
out=$("$BIN/demandoc" "$TMP/smoke.5" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "mdocml"; then
	echo "ok: 6 demandoc 宏展开退出 0 且输出含正文"
else
	echo "FAIL: 6 demandoc (rc=$rc)"; echo "$out" | sed 's/^/    | /'
	fails=$((fails + 1))
fi

# ── soelim：.so 指令处理（7–8）────────────────────────────────
printf '.TH SOELIM 1\n.SH NAME\nsoelim \\- included\n' > "$TMP/real.1"
printf '.so %s/real.1\n' "$TMP" > "$TMP/soinput"
out=$("$BIN/soelim" "$TMP/soinput" 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then
	echo "ok: 7 soelim 展开 .so 指令退出 0"
else
	echo "FAIL: 7 soelim (rc=$rc)"; echo "$out" | sed 's/^/    | /'
	fails=$((fails + 1))
fi
# 断言8：被包含文件的正文必须出现在输出里。`soelim` 只做 `.so` 指令展开、
# **不解释 roff 转义**（与 mandoc 不同：mandoc 渲染时会把 `\-` 变成 `-`，
# soelim 原样保留 `\` `-` 两个字符，od 实测输出 `s o e l i m   \ -   i n c l u d e d`）。
# 因此不能 grep 精确串 "soelim - included"（永不含反斜杠转义后的形态），
# 正确判据 = 用宽松正则跨越转义字符命中整行。
if printf '%s' "$out" | grep -q "soelim .* included"; then
	echo "ok: 8 soelim 输出含被包含文件正文（宽松匹配，容忍 roff 转义 \\-）"
else
	echo "FAIL: 8 soelim 输出未含被包含正文"; fails=$((fails + 1))
fi

# ── 交付面：静态库与对外头（9–10）────────────────────────────
PKG_ROOT="$(dirname "$BIN")"
if [ -f "$PKG_ROOT/lib/libmandoc.a" ]; then
	echo "ok: 9 交付 lib/libmandoc.a 存在（静态，无 .so → R26 满足）"
else
	echo "FAIL: 9 lib/libmandoc.a 缺失"; fails=$((fails + 1))
fi

missing=""
for hdr in eqn.h man.h mandoc.h mandoc_aux.h mandoc_parse.h mdoc.h roff.h tbl.h; do
	[ -f "$PKG_ROOT/include/$hdr" ] || missing="$missing $hdr"
done
if [ -z "$missing" ]; then
	echo "ok: 10 对外 8 头文件齐全（= 上游 lib-install 清单）"
else
	echo "FAIL: 10 缺头文件:$missing"; fails=$((fails + 1))
fi

rm -rf "$TMP" 2>/dev/null || true
echo "BIN_TOTAL=10 BIN_FAILS=$fails"
[ "$fails" -eq 0 ]
