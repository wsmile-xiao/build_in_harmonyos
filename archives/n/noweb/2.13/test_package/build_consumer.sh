#!/bin/sh
# build_consumer.sh — 鸿蒙化消费者用例（编译阶段）
#
# 端到端消费闭环：
#   1) 用被测包 noweb 的 notangle，把 hello.nw tangle 成 C 源码 hello.c
#      （模拟鸿蒙开发者的真实使用方式）；
#   2) 用鸿蒙工具链 clang（build 上下文注入）把 hello.c 编译为可执行文件
#      hello_ohos（aarch64 / OHOS ELF）；
#   3) 产物 hello_ohos 交由 test.sh 在本机(OHOS)运行断言 —— tangle→构建→运行
#      全链路在鸿蒙平台完成。
#
# 环境：由 test_package/conanfile.py build() 以 env=["conanrun","conanbuild"]
# 调用：conanrun 提供被测包 notangle，conanbuild 提供鸿蒙 clang。
set -e

cd "$(dirname "$0")" || exit 1

echo "[noweb consumer] notangle hello.nw -> hello.c"
notangle hello.nw > hello.c || { echo "FAIL: notangle hello.nw (rc=$?)" 1>&2; exit 1; }
grep -q "int main" hello.c || { echo "FAIL: hello.c has no main()" 1>&2; exit 1; }

cc="${CC:-clang}"
echo "[noweb consumer] ${cc} hello.c -o hello_ohos (OHOS aarch64)"
"$cc" hello.c -o hello_ohos || { echo "FAIL: clang build hello_ohos (rc=$?)" 1>&2; exit 1; }
echo "[noweb consumer] built hello_ohos OK"
