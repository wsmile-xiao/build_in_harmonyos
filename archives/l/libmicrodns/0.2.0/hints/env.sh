#!/bin/sh
# Environment setup for libmicrodns meson build
# This file is used by G0 clean-verify to set correct compiler paths

export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar

# Meson setup command with environment variables
# Usage: meson setup builddir --prefix=$DEFAULT_PREFIX