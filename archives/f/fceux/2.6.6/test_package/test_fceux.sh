#!/bin/sh
# test_package/test_fceux.sh — fceux 2.6.6 消费者冒烟测试
# 用法: test_fceux.sh <fceux 二进制绝对路径>（由 test_package/conanfile.py 调用）
# fceux 为 Qt GUI 应用，无头环境必须 QT_QPA_PLATFORM=offscreen；
# 上游 src/drivers/Qt/fceuWrapper.cpp 在 --version/--help 后直接 exit(0)，
# 不进入 Qt 事件循环，可做 headless 断言（flameshot/augustus-game 先例）。
set -eu

BIN="$1"
export QT_QPA_PLATFORM=offscreen

PASS=0
FAIL=0

run_case() {
  _name="$1"
  shift
  echo "[case] $_name: $*"
  if _out=$("$@" 2>&1); then
    echo "$_out"
    echo "[case] PASS: $_name"
    PASS=$((PASS + 1))
  else
    echo "$_out"
    echo "[case] FAIL: $_name (exit $?)"
    FAIL=$((FAIL + 1))
  fi
}

echo "[test] $BIN --version"
VOUT="$(QT_QPA_PLATFORM=offscreen "$BIN" --version 2>&1)"
echo "$VOUT"
case "$VOUT" in
  *2.6.6*)
    echo "[test] PASS: --version reports 2.6.6"
    PASS=$((PASS + 1))
    ;;
  *)
    echo "[test] FAIL: --version output missing 2.6.6"
    FAIL=$((FAIL + 1))
    ;;
esac

run_case "help-exits-zero" env QT_QPA_PLATFORM=offscreen "$BIN" --help

echo "RESULT: $PASS passed, $FAIL failed"
