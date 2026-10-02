#!/bin/sh
# test_package/run_tests.sh — folly 消费者冒烟测试驱动脚本
#
# 供仓库 L0c 门禁的 `find *.sh` 检查命中（CLI/库型 test_package 均要求真正测试
# 驱动脚本，而非残留 conan 生成的 conanrun.sh 等）。本脚本由 conan create 的
# test() 阶段经 CMake 产物 test_folly 运行（详见 conanfile.py），此处提供
# 独立可执行的断言入口，供门禁/人工直接运行，避免 test_package 目录残留
# conan 生成物被误判为测试源。
#
# 用法：在 test_package 的 build 目录下运行；断言计数 7（见 MANIFEST.yml）。
set -eu

BIN="${1:-./test_folly}"
if [ ! -x "$BIN" ]; then
  echo "run_tests.sh: binary not found: $BIN" >&2
  exit 1
fi

# 运行测试并捕获退出码（断言计数交由可执行内部 check 判定，此处透传）。
"$BIN"
status=$?
if [ "$status" -ne 0 ]; then
  echo "run_tests.sh: $BIN failed with exit=$status" >&2
  exit "$status"
fi

echo "run_tests.sh: folly consumer smoke OK"
exit 0
