#!/usr/bin/env bash
# capnproto 1.3.0 上游测试运行配置（OHOS /tmp、/var/tmp 只读平台）
#
# 用途：以合法可写目录策略恢复 12 项 filesystem-disk 上游测试
#   （filesystem-disk-test.c++ 原生支持 TEST_TMPDIR 环境变量，
#    getenv("TEST_TMPDIR") 优先于硬编码 /var/tmp）。
#
# 用法：
#   TMPDIR_TEST_ROOT=<可写目录> bash run-upstream-tests.sh [测试二进制目录]
#   默认 TEST_TMPDIR = ${TMPDIR_TEST_ROOT:-$HOME/tmp}（须为可写目录）
#
# 说明：
#   - 该配置仅影响测试运行环境，不修改任何上游源码；
#   - Serialize/FileDescriptors 的恢复由 patches/0001-serialize-test-use-test-tmpdir.patch 提供；
#   - 剩余 3 项（AF_UNIX 路径 bind / FALLOC_FL_PUNCH_HOLE / hardlink）为文件系统能力限制，
#     不因本配置而通过，属真实平台限制（详见 reports/test-report.md r02 段）。

set -u
# 说明：有意不使用 set -e（单个测试二进制非零退出不影响后续目标运行），
# 以便一次脚本跑完全部目标并逐项收集通过/失败结果；

TEST_TMPDIR="${TMPDIR_TEST_ROOT:-${HOME:-/storage/Users/currentUser}/tmp}"
BIN_DIR="${1:-.}"

if [ ! -w "$TEST_TMPDIR" ]; then
  echo "[ERROR] TEST_TMPDIR 不可写: $TEST_TMPDIR" >&2
  exit 2
fi

export TEST_TMPDIR
export TMPDIR="${TMPDIR:-$TEST_TMPDIR}"

echo "== capnproto 1.3.0 upstream test runner (TEST_TMPDIR=$TEST_TMPDIR) =="

run_one() {
  local bin="$1"
  if [ -x "$bin" ]; then
    echo "---- $bin ----"
    "$bin"
  else
    echo "!! binary not found: $bin (跳过；请先在 BUILD_TESTING=ON 构建目录编译测试目标)"
  fi
}

run_one "$BIN_DIR/kj-tests"
run_one "$BIN_DIR/capnp-tests"
run_one "$BIN_DIR/kj-heavy-tests"
run_one "$BIN_DIR/capnp-heavy-tests"
run_one "$BIN_DIR/capnp-evolution-tests"

echo "== done =="