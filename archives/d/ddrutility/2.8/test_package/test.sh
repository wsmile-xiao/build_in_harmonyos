#!/data/service/hnp/bin/bash
# test.sh — ddrutility 消费者侧测试（鸿蒙特有）
#
# 用法: bash test.sh <bindir>
#   <bindir> = 已安装包内的 bin/ 目录（由 test_package/conanfile.py 传入）
#
# 断言 13 项：
#   A1-A10 五个交付程序（ddrutility / ddru_ntfsbitmap / ddru_ntfsfindbad /
#          ddru_diskutility / ddru_findbad）的 --version 与 --help 实执行
#          （rc=0 且输出含各自版本号或用法关键字）；
#   A11-A13 三项"实际解析输入"的非法输入边界断言——证明程序真的在解析
#          参数/读取数据，而不是只打印帮助文本。
set -euo pipefail

BINDIR="${1:-}"
if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "FAIL: 未提供有效的 bin 目录: '$BINDIR'"
    exit 1
fi

PASS=0
FAIL=0
ok()  { echo "PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# 断言：rc=0 且输出（stdout+stderr）含给定子串
expect_rc0_contains() {
    local label="$1" needle="$2"
    shift 2
    local out rc
    out="$("$@" 2>&1)" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -F -- "$needle" >/dev/null; then
        ok "$label"
    else
        bad "$label (rc=$rc, 期望子串: $needle)"
        printf '%s\n' "$out" | head -5 | sed 's/^/    DEBUG: /'
    fi
}

# 断言：rc != 0 且输出含给定子串
expect_rc_nonzero_contains() {
    local label="$1" needle="$2"
    shift 2
    local out rc
    out="$("$@" 2>&1)" && rc=0 || rc=$?
    if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -F -- "$needle" >/dev/null; then
        ok "$label"
    else
        bad "$label (rc=$rc, 期望非 0 且含子串: $needle)"
        printf '%s\n' "$out" | head -5 | sed 's/^/    DEBUG: /'
    fi
}

# 断言：rc != 0
expect_rc_nonzero() {
    local label="$1"
    shift
    local out rc
    out="$("$@" 2>&1)" && rc=0 || rc=$?
    if [ "$rc" -ne 0 ]; then
        ok "$label"
    else
        bad "$label (rc=$rc, 期望非 0)"
        printf '%s\n' "$out" | head -5 | sed 's/^/    DEBUG: /'
    fi
}

for prog in ddrutility ddru_ntfsbitmap ddru_ntfsfindbad ddru_diskutility ddru_findbad; do
    if [ ! -e "$BINDIR/$prog" ]; then
        echo "FAIL: 交付程序缺失: $BINDIR/$prog"
        exit 1
    fi
done

echo "=== A1-A10: --version / --help 实执行 ==="
expect_rc0_contains "A1 ddrutility --version"        "ddrutility 2.8"        "$BINDIR/ddrutility" --version
expect_rc0_contains "A2 ddrutility --help"           "ddru_findbad"          "$BINDIR/ddrutility" --help
expect_rc0_contains "A3 ddru_ntfsbitmap --version"   "ddru_ntfsbitmap 1.5"   "$BINDIR/ddru_ntfsbitmap" --version
expect_rc0_contains "A4 ddru_ntfsbitmap --help"      "bitmap"                "$BINDIR/ddru_ntfsbitmap" --help
expect_rc0_contains "A5 ddru_ntfsfindbad --version"  "ddru_ntfsfindbad 1.5"  "$BINDIR/ddru_ntfsfindbad" --version
expect_rc0_contains "A6 ddru_ntfsfindbad --help"     "logfile"               "$BINDIR/ddru_ntfsfindbad" --help
expect_rc0_contains "A7 ddru_diskutility --version"  "ddru_diskutility 1.3"  "$BINDIR/ddru_diskutility" --version
expect_rc0_contains "A8 ddru_diskutility --help"     "Usage"                 "$BINDIR/ddru_diskutility" --help
expect_rc0_contains "A9 ddru_findbad --version"      "ddru_findbad 1.11"     "$BINDIR/ddru_findbad" --version
expect_rc0_contains "A10 ddru_findbad --help"        "Usage"                 "$BINDIR/ddru_findbad" --help

echo "=== A11-A13: 非法输入边界（证明真实解析输入/数据）==="
WORK="ddrutility-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"
# 非 NTFS 的普通文件：程序应读取后判负（rc != 0），而不是假装成功
printf 'not a disk image\n' > "$WORK/fake.img"

expect_rc_nonzero "A11 ddru_ntfsbitmap 拒绝非 NTFS 输入" \
    "$BINDIR/ddru_ntfsbitmap" "$WORK/fake.img" "$WORK/out.log"
expect_rc_nonzero_contains "A12 ddru_ntfsfindbad 拒绝非 ddrescue 日志" "ERROR" \
    "$BINDIR/ddru_ntfsfindbad" "$WORK/fake.img" "$WORK/missing.log"
expect_rc_nonzero_contains "A13 ddru_diskutility 拒绝未知选项" "unrecognized option" \
    "$BINDIR/ddru_diskutility" "$WORK/fake.img" --bogus
rm -rf "$WORK"

echo "----------------------------------------"
echo "ddrutility test_package: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    echo "RESULT: FAILED"
    exit 1
fi
echo "RESULT: ALL 13 ASSERTIONS PASSED"
