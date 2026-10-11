#!/bin/bash
# yuview 编译环境依赖
# 在编译前 source 此文件设置必要的环境变量

# ============================================================
# 关键依赖：OHOS SDK 链接器库路径
# ============================================================
# lld 链接器依赖 libxml2.so.16，必须设置此路径
# 否则链接阶段会报错
# "Error loading shared library libxml2.so.16 (needed by .../llvm/bin/lld)"
# 并伴随 xmlFreeDoc / xmlReadMemory 等 symbol not found 重定位失败。
# 注意：本文件仅为人工复现/排障提供环境固化参考；
#       conanfile.py 的 build() 已通过 _lld_environment() 自动注入同一路径，
#       不需要在 CI 中额外 source。
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:${LD_LIBRARY_PATH:-}"

# ============================================================
# 编译器设置（继承全局环境）
# ============================================================
# CC=clang, CXX=clang++ 由 conan profile（tools.build:compiler_executables）
# 提供；CFLAGS=-fPIC -O2 由全局环境设置
