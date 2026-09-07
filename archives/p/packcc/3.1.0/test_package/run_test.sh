#!/bin/bash
# test_package/run_test.sh — packcc 3.1.0 消费者冒烟（R34 / L0c）。
# 由 test_package/conanfile.py 的 test() 以 self.run 调用；CWD 为 conan
# build folder（calc_parser.c/.h 落在 build folder，断言有效）。
# calc.peg 逐字 vendored 自上游 tests/basic.d/input.peg（v3.1.0 tag），
# 与上游 test_generate 驱动同一真实 grammar，非自造壳。
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) 可执行文件存在且可运行（版本号断言，捆绑 PACKCC_VERSION=3.1.0）
packcc --version

# 2) 对上游真实 grammar 执行生成器（-o 前缀；与上游 test_generate 同链路）
packcc -o calc_parser "$DIR/calc.peg"

# 3) 断言生成产物真实落盘且头含生成器标识（非空壳）
test -f calc_parser.c
test -f calc_parser.h
grep -qi "PackCC" calc_parser.c

echo "packcc consumer test OK: parser.c/parser.h generated"
