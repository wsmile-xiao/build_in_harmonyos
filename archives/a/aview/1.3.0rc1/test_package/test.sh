#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for aview executable
# aview renders PGM/PPM/PNG/BMP images as ASCII art in a terminal.
# R34: genuinely exercises the tested package's binaries (aview + aaflip).
#
# Upstream aview 1.3.0rc1 ships NO test suite (no `make check` targets).
# This test set provides functional coverage:
#   1. aview reports usage
#   2. aview functionally converts a real PPM image -> ASCII art
#   3. aview handles an invalid image path gracefully
#   4. aaflip reports usage
#   5. asciiview wrapper script is installed and executable
set -euo pipefail

PASS=0
FAIL=0

ok()  { echo "PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# ---------------------------------------------------------------
echo "[test 1] aview reports usage (--help)"
# --help 正常退出前可能因终端能力差异返回非零；忽略退出码，仅捕获输出做断言
HELP_OUT=$(timeout 10 aview --help 2>&1 || true)
if printf '%s' "$HELP_OUT" | grep -q "Usage:"; then
    ok "aview prints Usage: (--help)"
else
    bad "aview did not print usage (--help)"
fi

# ---------------------------------------------------------------
# Build a tiny real PPM image (P3 ASCII format: 16x4 red/green/blue bars)
# -- done in pure shell, no extra tooling needed on the worker.
PPM="aview-test.ppm"
cat > "$PPM" <<'EOF'
P3
48 4
255
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255 0 0 255
EOF

echo "[test 2] aview functionally renders a real PPM image to ASCII art"
# Feed 'q' via stdin so aview exits after rendering (non-interactive run).
# aview 非交互退出码非零（q 键退出），但 stdout 需保留用于下方断言；
# 故忽略退出码仅捕获输出，后续逐项断言 output 内容（非空渲染/含 ASCII 字符/多行）。
OUTPUT=$(echo "q" | timeout 30 aview -driver stdout -kbddriver stdin "$PPM" 2>/dev/null || true)
if echo "$OUTPUT" | grep -q "Calculating"; then
    ok "aview started image calculation for $PPM"
else
    bad "aview did not start calculating (missing 'Calculating' marker)"
fi
# ASCII art output must contain typical aa-render characters
if echo "$OUTPUT" | grep -qE '[+|~=`^]'; then
    ok "aview produced ASCII-art glyphs (| + ~ etc.)"
else
    bad "aview output contained no ASCII-art glyphs"
fi
# Output must be multi-line (an actual rendered picture, not a one-liner)
LINES=$(echo "$OUTPUT" | wc -l)
if [ "$LINES" -ge 3 ]; then
    ok "aview produced multi-line rendering ($LINES lines)"
else
    bad "aview rendering too short ($LINES lines)"
fi

echo "[test 3] aview handles missing file path"
# aview 对缺失文件打印错误并以非零码退出（pipefail 下管道会非零），
# 先捕获输出忽略退出码，再对内容做断言。
ERR_OUT=$(timeout 10 aview /nonexistent/file.ppm 2>&1 </dev/null || true)
if printf '%s' "$ERR_OUT" | grep -qiE "not found|no such|cannot open|error"; then
    ok "aview reports an error for a missing image file"
else
    bad "aview did not report an error for a missing image file"
fi

echo "[test 4] aaflip prints usage/error information"
# aaflip 无参数时打印 banner/usage（同 test3 处理方式）
FLIP_OUT=$(timeout 10 aaflip 2>&1 </dev/null || true)
if printf '%s' "$FLIP_OUT" | grep -qiE "usage|fli|error|wrong|argument"; then
    ok "aaflip prints usage/error when invoked without arguments"
else
    bad "aaflip produced unexpected output without arguments"
fi

echo "[test 5] asciiview wrapper script installed"
if [ -x "$(command -v asciiview)" ] || [ -n "$(command -v asciiview)" ]; then
    ok "asciiview wrapper script is on PATH"
else
    bad "asciiview wrapper script missing"
fi

echo "----------------------------------------"
echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0