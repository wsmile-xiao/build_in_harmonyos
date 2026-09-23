#!/usr/bin/env bash
# test_package/run_tests.sh — odinfmt 包端到端测试驱动（5 项）
#
# 用法: run_tests.sh <odinfmt_bin> <pkg_dir> <work_dir>
#   odinfmt_bin : 包内 bin/odinfmt 绝对路径
#   pkg_dir     : odinfmt 包根（保留参数位，供诊断使用）
#   work_dir    : 测试产物输出目录
#
# 由 test_package/conanfile.py 的 test() 调用；也可脱离 conan 手工复现。
set -euo pipefail

ODINFMT_BIN="$1"
PKG_DIR="$2"
WORK_DIR="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$HERE/odinfmt.json"

# 测试产物落在独立子目录，退出时清理，避免污染调用方的 test_package 目录
WORK_DIR="$WORK_DIR/odinfmt_test_run"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "[test] 1/5 无参数调用 → Usage + 非 0 退出（CLI 契约）"
set +e
OUT="$("$ODINFMT_BIN" 2>&1)"
RC=$?
set -e
printf '%s\n' "$OUT" | head -3
if [ "$RC" -eq 0 ]; then
    echo "[test] FAIL: 无参数调用应返回非 0" >&2
    exit 1
fi
case "$OUT" in
    *"Missing path to format"*) ;;
    *) echo "[test] FAIL: 缺少 'Missing path to format' 提示" >&2; exit 1 ;;
esac

echo "[test] 2/5 文件模式：sample.odin 格式化输出与 expected.odin 逐字节一致"
"$ODINFMT_BIN" -config:"$CONFIG" "$HERE/sample.odin" > "$WORK_DIR/file_mode.odin"
if ! diff -u "$HERE/expected.odin" "$WORK_DIR/file_mode.odin"; then
    echo "[test] FAIL: 文件模式输出与期望不一致" >&2
    exit 1
fi

echo "[test] 3/5 幂等性：对 expected.odin 再格式化，结果逐字节不变"
"$ODINFMT_BIN" -config:"$CONFIG" "$HERE/expected.odin" > "$WORK_DIR/idempotent.odin"
if ! diff -u "$HERE/expected.odin" "$WORK_DIR/idempotent.odin"; then
    echo "[test] FAIL: 格式化非幂等" >&2
    exit 1
fi

echo "[test] 4/5 stdin 模式：-stdin 输出与文件模式一致"
"$ODINFMT_BIN" -config:"$CONFIG" -stdin < "$HERE/sample.odin" > "$WORK_DIR/stdin_mode.odin"
if ! diff -u "$HERE/expected.odin" "$WORK_DIR/stdin_mode.odin"; then
    echo "[test] FAIL: stdin 模式输出与文件模式不一致" >&2
    exit 1
fi

echo "[test] 5/5 -w 写回模式：目标文件被改写为期望内容且不残留 *_bk 备份"
cp "$HERE/sample.odin" "$WORK_DIR/write_mode.odin"
"$ODINFMT_BIN" -config:"$CONFIG" -w "$WORK_DIR/write_mode.odin"
if ! diff -u "$HERE/expected.odin" "$WORK_DIR/write_mode.odin"; then
    echo "[test] FAIL: -w 写回内容与期望不一致" >&2
    exit 1
fi
if [ -e "$WORK_DIR/write_mode.odin_bk" ]; then
    echo "[test] FAIL: 残留备份文件 write_mode.odin_bk" >&2
    exit 1
fi

echo "[test] 5/5 全部通过（odinfmt 包根: ${PKG_DIR}）"
