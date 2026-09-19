#!/usr/bin/env bash
# test_package/run_tests.sh — odin 包端到端测试驱动（3 项）
#
# 用法: run_tests.sh <odin_bin> <odin_root> <work_dir>
#   odin_bin  : 包内 bin/odin 绝对路径
#   odin_root : ODIN_ROOT（包根，base/core/shared/vendor 所在目录）
#   work_dir  : 编译产物输出目录
#
# 由 test_package/conanfile.py 的 test() 调用；也可脱离 conan 手工复现。
set -euo pipefail

ODIN_BIN="$1"
ODIN_ROOT_DIR="$2"
WORK_DIR="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"

export ODIN_ROOT="$ODIN_ROOT_DIR"
mkdir -p "$WORK_DIR"

echo "[test] 1/3 odin version（须含 dev-2026-08）"
VERSION_OUT="$("$ODIN_BIN" version)"
printf '%s\n' "$VERSION_OUT"
case "$VERSION_OUT" in
    *dev-2026-08*) ;;
    *) echo "[test] FAIL: version 输出未包含 dev-2026-08" >&2; exit 1 ;;
esac

echo "[test] 2/3 odin build hello.odin -file 并运行"
"$ODIN_BIN" build "$HERE/hello.odin" -file -out:"$WORK_DIR/hello_probe"
"$WORK_DIR/hello_probe"

echo "[test] 3/3 自举验证: odin build math_probe.odin -file 并运行"
"$ODIN_BIN" build "$HERE/math_probe.odin" -file -out:"$WORK_DIR/math_probe"
"$WORK_DIR/math_probe"

echo "[test] 3/3 全部通过"
