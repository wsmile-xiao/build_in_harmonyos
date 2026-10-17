#!/data/service/hnp/bin/bash
# test_dump1090.sh — dump1090-fa test_package 消费者测试
# 真实执行已安装的 dump1090 二进制（R34），验证版本输出与帮助信息。
# 用法: bash test_dump1090.sh <bin_dir>
set -u

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
DUMP1090="$BIN_DIR/dump1090"
VIEW1090="$BIN_DIR/view1090"
FAUP1090="$BIN_DIR/faup1090"
STARCH="$BIN_DIR/starch-benchmark"

PASS=0
FAIL=0

check() {
    # check <desc> <cmd...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $desc"
        PASS=$((PASS+1))
    else
        echo "FAIL: $desc"
        FAIL=$((FAIL+1))
    fi
}

echo "== dump1090-fa 8.0 consumer tests =="

# 1. 四个二进制均存在且可执行
check "dump1090 exists" test -x "$DUMP1090"
check "view1090 exists" test -x "$VIEW1090"
check "faup1090 exists" test -x "$FAUP1090"
check "starch-benchmark exists" test -x "$STARCH"

# 2. dump1090 --version 输出包含 8.0
VER_OUT=$("$DUMP1090" --version 2>&1)
if echo "$VER_OUT" | grep -q "8\.0"; then
    echo "PASS: dump1090 --version reports 8.0 ($VER_OUT)"
    PASS=$((PASS+1))
else
    echo "FAIL: dump1090 --version output: $VER_OUT"
    FAIL=$((FAIL+1))
fi

# 3. dump1090 --help 可用（退出码 0）
check "dump1090 --help" "$DUMP1090" --help
check "view1090 --help" "$VIEW1090" --help
check "faup1090 --help" "$FAUP1090" --help

echo "== result: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ]
