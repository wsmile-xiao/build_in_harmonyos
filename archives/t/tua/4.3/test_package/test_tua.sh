#!/usr/bin/env bash
# test_tua.sh — tua 消费者侧真实功能测试（实质运行被测二进制，R34）
#
# 用法: bash test_tua.sh <package_bin_dir>
#
# 测试思路：构造一个合成的 Taylor UUCP spool 目录（Stats + Log），用 tua
# 解析并校验报表输出；另含 1 项鸿蒙平台专有用例（AArch64 / OHOS ELF 产物）。
set -u

BIN_DIR="${1:?usage: test_tua.sh <package_bin_dir>}"
TUA="$BIN_DIR/tua"

TMPBASE="${TMPDIR:-$HOME/tmp}"
WORK="$TMPBASE/tua-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK/spool"
SPOOL="$WORK/spool"

# ── 合成 Taylor UUCP 数据（Taylor 的 Stats/Log 格式）─────────────────────
cat > "$SPOOL/Stats" <<'EOF'
alice alpha (2013-05-01 10:00:00.00) sent 10240 bytes in 60 seconds (170 bytes/sec) on port ttyS0
bob alpha (2013-05-01 10:05:00.00) received 20480 bytes in 120 seconds (170 bytes/sec) on port ttyS0
alice beta (2013-05-02 11:00:00.00) sent 5120 bytes in 30 seconds (170 bytes/sec) on port ttyS1
EOF

cat > "$SPOOL/Log" <<'EOF'
uucico alpha alice (2013-05-01 10:00:00.00 1234) Calling system alpha (port ttyS0)
uucico beta bob (2013-05-02 11:00:00.00 1235) Calling system beta (port ttyS1)
EOF

PASS=0
FAIL=0
declare -a NAMES=()

# check <name> <0|1>
check() {
  if [ "$2" -eq 0 ]; then
    echo "PASS: $1"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $1"
    FAIL=$((FAIL + 1))
  fi
  NAMES+=("$1")
}

# run_tua <args...>  -> stdout into $OUT (stderr merged)
OUT=""
run_tua() {
  OUT="$("$TUA" "$@" 2>&1)"
  RC=$?
}

echo "=== tua test_package (binary: $TUA) ==="

# ── TC-01 版本横幅 ───────────────────────────────────────────────────────
run_tua -V
echo "$OUT" | grep -q "The Uucp Analyzer (TUA) rel. 4.3"
check "TC-01-version" $?
[ "$RC" -eq 0 ]; check "TC-01b-version-exit0" $?

# ── TC-02 用法/帮助 ──────────────────────────────────────────────────────
run_tua -i
echo "$OUT" | grep -q -- "--prefix-path"
check "TC-02-usage" $?

# ── TC-03 按系统报表（解析合成 Stats/Log）────────────────────────────────
run_tua -p "$SPOOL"
echo "$OUT" | grep -q "By System:"
check "TC-03-system-report" $?
echo "$OUT" | grep -q "^alpha"
check "TC-03b-system-alpha" $?
echo "$OUT" | grep -q "^beta"
check "TC-03c-system-beta" $?
[ "$RC" -eq 0 ]; check "TC-03d-exit0" $?

# ── TC-04 字节量统计（SUMMARY 段按字节，逐系统）─────────────────────────
echo "$OUT" | grep -q "20480"
check "TC-04a-bytes-received" $?
echo "$OUT" | grep -q "10240"
check "TC-04b-bytes-sent" $?
echo "$OUT" | grep -q "5120"
check "TC-04c-bytes-beta" $?

# ── TC-05 按用户报表 ─────────────────────────────────────────────────────
echo "$OUT" | grep -q "By User:"
check "TC-05a-user-report" $?
echo "$OUT" | grep -q "^alice"
check "TC-05b-user-alice" $?
echo "$OUT" | grep -q "^bob"
check "TC-05c-user-bob" $?

# ── TC-06 系统别名替换（-s alpha=ALPHA）──────────────────────────────────
run_tua -p "$SPOOL" -s alpha=ALPHA
echo "$OUT" | grep -q "^ALPHA"
check "TC-06-system-alias" $?
echo "$OUT" | grep -q "^beta"
check "TC-06b-unaliased-kept" $?

# ── TC-07 过滤：仅 alpha 系统的 SUMMARY ──────────────────────────────────
run_tua -p "$SPOOL" -O alpha -S -U -D -m -h -y
echo "$OUT" | grep -q "SUMMARY by System:"
check "TC-07a-only-system-summary" $?
echo "$OUT" | grep -q "^alpha:"
check "TC-07b-only-system-alpha" $?
echo "$OUT" | grep -q "^beta:" && check "TC-07c-only-system-beta-absent" 1 \
                               || check "TC-07c-only-system-beta-absent" 0

# ── TC-08 仅小时活动图（-o）──────────────────────────────────────────────
run_tua -p "$SPOOL" -o
echo "$OUT" | grep -q "Hourly Activity"
check "TC-08-hourly-chart" $?

# ── TC-09 国家/费率配置输出 ──────────────────────────────────────────────
run_tua --print-country
echo "$OUT" | grep -q "country"
check "TC-09-print-country" $?

# ── TC-10【鸿蒙特有】产物 AArch64 / OHOS ELF 断言 ────────────────────────
MAGIC="$(od -An -tx1 -N4 "$TUA" | tr -d ' \n')"          # 7f454c46
CLASS="$(od -An -tx1 -j4 -N1 "$TUA" | tr -d ' \n')"      # 02 = ELFCLASS64
MACHINE="$(od -An -tx1 -j18 -N2 "$TUA" | tr -d ' \n')"   # b700 = EM_AARCH64(LE)
case "$MAGIC:$CLASS:$MACHINE" in
  7f454c46:02:b700) check "TC-10-ohos-abi" 0 ;;
  *)                check "TC-10-ohos-abi" 1 ;;
esac
# musl 解释器（/lib/ld-musl-aarch64.so.1）：以 od 十六进制方式搜索，
# 避免依赖 grep 对二进制文件的支持（toybox grep 不检索二进制内容）。
INTERP_HEX="$(printf '%s' '/lib/ld-musl-aarch64.so.1' | od -An -tx1 | tr -d ' \n')"
od -An -tx1 -v "$TUA" | tr -d ' \n' | grep -q "$INTERP_HEX"
check "TC-10b-ohos-interp" $?

# ── 汇总 ─────────────────────────────────────────────────────────────────
rm -rf "$WORK"
echo "-----------------------------------------"
echo "TOTAL=$((PASS + FAIL)) PASS=$PASS FAIL=$FAIL"
echo "CASES: ${NAMES[*]}"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
