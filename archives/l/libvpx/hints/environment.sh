#!/bin/bash
# libvpx 编译环境依赖
# 在编译前 source 此文件设置必要的环境变量

# ============================================================
# 关键依赖：OHOS SDK 链接器库路径
# ============================================================
# lld 链接器依赖 libxml2.so.16，必须设置此路径
# 否则 configure 会报错 "Toolchain is unable to link executables"
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:${LD_LIBRARY_PATH:-}"

# ============================================================
# 工具依赖
# ============================================================
# libvpx configure 需要 diff 工具
# 使用 GNU diff（已安装到 ~/usr/local/bin）
export PATH="/storage/Users/currentUser/usr/local/bin:${PATH:-}"

# ============================================================
# 编译器设置（继承全局环境）
# ============================================================
# CC=clang, CXX=clang++ 由全局环境设置
# CFLAGS=-fPIC -O2 由全局环境设置