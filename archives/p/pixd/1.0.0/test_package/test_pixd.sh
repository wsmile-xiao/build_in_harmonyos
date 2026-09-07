#!/data/service/hnp/bin/bash
# test_package/test_pixd.sh — pixd consumer + functional tests
#
# Runs inside the conanrun environment (PATH includes the installed bin/ dir).
# R34: every test genuinely runs the pixd binary and asserts on its real output.
#
# Two groups:
#   [消费者 Consumer C]  — end-user / consumer perspective on the installed executable
#   [功能 Functional F]  — assert pixd's real rendering features (-w/-r/PIXD_COLORS/...)
#
# Any failed assertion prints "FAIL: ..." and exits non-zero (the conan L1 test
# then reports the whole test_package as failed). All assertions were validated
# against the real OHOS aarch64 pixd binary (pixd.c 1.0.0 + 0001 patch).
set -eu

# Work dir: /tmp is read-only on some OHOS devices, honour $TMPDIR when set.
d="${TMPDIR:-/tmp}/pixd-test.$$"
mkdir -p "$d" || { echo "FAIL: cannot create work dir $d"; exit 1; }
trap 'rm -rf "$d"' EXIT

CASE=0
ASSERT=0
fail() { echo "FAIL: $1" >&2; exit 1; }
case_ok() { CASE=$((CASE + 1)); }
assert_ok() { ASSERT=$((ASSERT + 1)); }

# ---- sample-binary generators (printf-only, shell-portable) ----------------
# gen_seq_file <file> <count> : writes count bytes whose value == index (0..count-1)
gen_seq_file() {
    local f="$1" n="$2" i=0 oct
    : > "$f"
    while [ "$i" -lt "$n" ]; do
        oct=$(printf '%03o' "$i")
        printf "\\$oct" >> "$f"
        i=$((i + 1))
    done
}
# gen_mod_file <file> <count> : writes count bytes whose value == index % 256
gen_mod_file() {
    local f="$1" n="$2" i=0 v oct
    : > "$f"
    while [ "$i" -lt "$n" ]; do
        v=$((i % 256))
        oct=$(printf '%03o' "$v")
        printf "\\$oct" >> "$f"
        i=$((i + 1))
    done
}

# 24-bit SGR foreground escape prefix, e.g. ESC[38;2;R;G;Bm
SGR_FG=$'\x1b[38;2;'

echo "================ 消费者测试 (Consumer) ================"

# --- C1: 可执行性与 PATH：conanrun 内可发现并执行 pixd ---------------------
echo "[C1] 可执行性/PATH：command -v pixd 成功且为可执行文件"
PIXD_BIN=$(command -v pixd) || fail "C1: pixd not found on PATH"
assert_ok
test -n "$PIXD_BIN" || fail "C1: command -v returned empty path"
assert_ok
test -x "$PIXD_BIN" || fail "C1: '$PIXD_BIN' is not executable"
assert_ok
case_ok
echo "OK: C1 pixd discoverable + executable ($PIXD_BIN)"

# --- C2: --version：exit 0 且输出含 "pixd 1.0.0" ----------------------------
echo "[C2] --version：exit 0 且输出含 'pixd 1.0.0'"
if pixd --version > "$d/c2.out" 2> "$d/c2.err"; then :; else fail "C2: --version exit != 0"; fi
assert_ok
grep -q "pixd 1.0.0" "$d/c2.out" || fail "C2: --version output missing 'pixd 1.0.0'"
assert_ok
case_ok
echo "OK: C2 --version shows pixd 1.0.0"

# --- C3: --help：exit 0 且输出含 "usage: pixd" ------------------------------
echo "[C3] --help：exit 0 且输出含 'usage: pixd'"
if pixd --help > "$d/c3.out" 2> "$d/c3.err"; then :; else fail "C3: --help exit != 0"; fi
assert_ok
grep -q "usage: pixd" "$d/c3.out" || fail "C3: --help output missing 'usage: pixd'"
assert_ok
case_ok
echo "OK: C3 --help shows usage"

# --- C4: 空 stdin：exit 0 且无输出 ------------------------------------------
echo "[C4] 空 stdin：exit 0 且无输出"
if printf '' | pixd > "$d/c4.out" 2> "$d/c4.err"; then :; else fail "C4: empty stdin exit != 0"; fi
assert_ok
test ! -s "$d/c4.out" || fail "C4: empty stdin produced output"
assert_ok
case_ok
echo "OK: C4 empty stdin is silent (exit 0)"

echo "================ 功能测试 (Functional) ================"

# --- F1: stdin 模式：输出含偏移列与 24-bit SGR -----------------------------
echo "[F1] stdin 模式：输出含偏移 '0000' 与 SGR '38;2;'"
if printf 'pixd functional stdin input 0123456789\n' | pixd > "$d/f1.out" 2> "$d/f1.err"; then :; else fail "F1: stdin exit != 0"; fi
assert_ok
grep -q "    0000" "$d/f1.out" || fail "F1: stdin output missing offset column '    0000'"
assert_ok
grep -qF "$SGR_FG" "$d/f1.out" || fail "F1: stdin output missing 24-bit SGR 'ESC[38;2;'"
assert_ok
case_ok
echo "OK: F1 stdin renders offset header + SGR colours"

# --- F2: 文件参数模式：exit 0 且输出含偏移列 --------------------------------
echo "[F2] 文件参数模式：exit 0 且输出含偏移列"
gen_mod_file "$d/f2.bin" 64
if pixd "$d/f2.bin" > "$d/f2.out" 2> "$d/f2.err"; then :; else fail "F2: file mode exit != 0"; fi
assert_ok
grep -q "    0000" "$d/f2.out" || fail "F2: file mode output missing offset column"
assert_ok
case_ok
echo "OK: F2 file mode renders file with offset header"

# --- F3: 未知选项（如 -Z）：exit != 0 ---------------------------------------
echo "[F3] 未知选项 -Z：exit != 0"
if pixd -Z > /dev/null 2>&1; then fail "F3: unknown option -Z accepted (exit 0)"; else :; fi
assert_ok
case_ok
echo "OK: F3 unknown option rejected (exit != 0)"

# --- F4: -w 宽度影响行结构：33B + -w8 出现 0010/0020（默认 64 不出现） ------
echo "[F4] -w 宽度：33 字节 + '-w 8' 输出含偏移 '0010' 与 '0020'"
gen_seq_file "$d/f4.bin" 33
if pixd -w 8 "$d/f4.bin" > "$d/f4.out" 2> "$d/f4.err"; then :; else fail "F4: -w 8 exit != 0"; fi
assert_ok
grep -q "    0010" "$d/f4.out" || fail "F4: -w 8 output missing second-line offset '0010'"
assert_ok
grep -q "    0020" "$d/f4.out" || fail "F4: -w 8 output missing third-line offset '0020'"
assert_ok
case_ok
echo "OK: F4 -w 8 changes line structure (16 bytes/line)"

# --- F5: 多文件 banner：含 "====>" 与两个文件名 -----------------------------
echo "[F5] 多文件：banner '====>' 含两个文件名"
printf 'alpha' > "$d/f5a.bin"
printf 'beta'  > "$d/f5b.bin"
if pixd "$d/f5a.bin" "$d/f5b.bin" > "$d/f5.out" 2> "$d/f5.err"; then :; else fail "F5: multi-file exit != 0"; fi
assert_ok
grep -q '====>' "$d/f5.out" || fail "F5: multi-file output missing '====>' banner"
assert_ok
grep -q 'f5a.bin' "$d/f5.out" || fail "F5: banner missing first filename"
assert_ok
grep -q 'f5b.bin' "$d/f5.out" || fail "F5: banner missing second filename"
assert_ok
case_ok
echo "OK: F5 multi-file banners show both filenames"

# --- F6: -r 绝对范围：256B 文件 + '-r 16-31' 首行偏移 0010 且无 0000 --------
echo "[F6] -r 绝对范围：'-r 16-31' 首行偏移 '0010' 且不含 '0000'"
gen_seq_file "$d/f6.bin" 256
if pixd -r 16-31 "$d/f6.bin" > "$d/f6.out" 2> "$d/f6.err"; then :; else fail "F6: -r 16-31 exit != 0"; fi
assert_ok
grep -q "    0010" "$d/f6.out" || fail "F6: range output missing start offset '0010'"
assert_ok
if grep -q "    0000" "$d/f6.out"; then fail "F6: range output unexpectedly contains offset '0000'"; else :; fi
assert_ok
case_ok
echo "OK: F6 -r absolute range starts at 0010"

# --- F7: -r 相对范围：'-r 16+8' 输出含 '0010' -------------------------------
echo "[F7] -r 相对范围：'-r 16+8' 输出含偏移 '0010'"
if pixd -r 16+8 "$d/f6.bin" > "$d/f7.out" 2> "$d/f7.err"; then :; else fail "F7: -r 16+8 exit != 0"; fi
assert_ok
grep -q "    0010" "$d/f7.out" || fail "F7: relative-range output missing offset '0010'"
assert_ok
case_ok
echo "OK: F7 -r relative range renders from 0010"

# --- F8: -r 非法输入：exit != 0 且 stderr 有输出 ----------------------------
echo "[F8] -r 非法输入 'abc'：exit != 0 且 stderr 有输出"
if pixd -r abc "$d/f6.bin" > "$d/f8.out" 2> "$d/f8.err"; then fail "F8: invalid range accepted (exit 0)"; else :; fi
assert_ok
test -s "$d/f8.err" || fail "F8: no stderr output for invalid range"
assert_ok
case_ok
echo "OK: F8 invalid range rejected with stderr"

# --- F9: PIXD_COLORS 合法：256 色第 1 色 010203，输入 0x00 → 38;2;1;2;3 -----
echo "[F9] PIXD_COLORS 合法：256 色(首色 010203)，输入 0x00 输出 '38;2;1;2;3'"
{
    printf '010203'
    i=1
    while [ "$i" -lt 256 ]; do printf ' ffffff'; i=$((i + 1)); done
    printf '\n'
} > "$d/f9.colors"
F9_COLORS=$(cat "$d/f9.colors")
if printf '\000' | PIXD_COLORS="$F9_COLORS" pixd > "$d/f9.out" 2> "$d/f9.err"; then :; else fail "F9: 256-colour PIXD_COLORS exit != 0"; fi
assert_ok
grep -q '38;2;1;2;3' "$d/f9.out" || fail "F9: output missing overridden colour '38;2;1;2;3'"
assert_ok
case_ok
echo "OK: F9 PIXD_COLORS overrides colormap entry"

# --- F10: PIXD_COLORS 非法（仅 3 色）：exit != 0 且 stderr 含 PIXD_COLORS ---
echo "[F10] PIXD_COLORS 非法(3 色)：exit != 0 且 stderr 含 'PIXD_COLORS'"
if printf '\000' | PIXD_COLORS='010203 ffffff 000000' pixd > "$d/f10.out" 2> "$d/f10.err"; then
    fail "F10: 3-colour PIXD_COLORS accepted (exit 0)"
else
    :
fi
assert_ok
grep -q 'PIXD_COLORS' "$d/f10.err" || fail "F10: stderr missing 'PIXD_COLORS'"
assert_ok
case_ok
echo "OK: F10 invalid PIXD_COLORS rejected on stderr"

# --- F11: 字节→颜色映射：单字节 0xFF → 38;2;255;255;255 --------------------
echo "[F11] 字节映射：单字节 0xFF 输出 '38;2;255;255;255'"
if printf '\377' | pixd > "$d/f11.out" 2> "$d/f11.err"; then :; else fail "F11: 0xFF input exit != 0"; fi
assert_ok
grep -q '38;2;255;255;255' "$d/f11.out" || fail "F11: 0xFF byte not mapped to white (255;255;255)"
assert_ok
case_ok
echo "OK: F11 0xFF maps to fg 255;255;255"

# --- F12: 大文件跨行偏移：300B 默认宽度含 '0080' 与 '0100' ------------------
echo "[F12] 大文件跨行偏移：300 字节默认宽度含偏移 '0080' 与 '0100'"
gen_mod_file "$d/f12.bin" 300
if pixd "$d/f12.bin" > "$d/f12.out" 2> "$d/f12.err"; then :; else fail "F12: 300-byte file exit != 0"; fi
assert_ok
grep -q "    0080" "$d/f12.out" || fail "F12: missing line offset '0080'"
assert_ok
grep -q "    0100" "$d/f12.out" || fail "F12: missing line offset '0100'"
assert_ok
case_ok
echo "OK: F12 300-byte file renders offsets 0080/0100"

echo ""
echo "pixd test_package: ALL PASS (${CASE} test cases, ${ASSERT} assertions)"
