#!/bin/sh
# test_package 功能测试：验证 julius 二进制可运行 + 参数解析行为
# 用法: test.sh <julius路径> <输出目录>
set -e

JULIUS="$1"
OUT_DIR="$2"

if [ ! -x "$JULIUS" ]; then
    echo "[fail] julius not found at $JULIUS"
    exit 1
fi

# 正例：--help 应输出 Usage 字样（退出码非 0 属预期，用输出内容断言）
set +e
"$JULIUS" --help > "$OUT_DIR/help.out" 2>&1
HELP_RC=$?
set -e

if ! grep -q "Usage: julius" "$OUT_DIR/help.out"; then
    echo "[fail] julius --help did not print usage (rc=$HELP_RC)"
    exit 1
fi
echo "[pass] julius --help prints usage (rc=$HELP_RC, expected non-zero)"

# 负例（E003）：非法参数必须被拒绝（退出码非 0 + 输出含 not recognized）
set +e
"$JULIUS" --definitely-invalid-option > "$OUT_DIR/bad.out" 2>&1
BAD_RC=$?
set -e

if [ "$BAD_RC" -eq 0 ]; then
    echo "[fail] julius accepted an invalid option (rc=0)"
    exit 1
fi
if ! grep -q "not recognized" "$OUT_DIR/bad.out"; then
    echo "[fail] julius did not reject invalid option (rc=$BAD_RC)"
    exit 1
fi
echo "[pass] julius rejects invalid option (rc=$BAD_RC, output contains 'not recognized')"
