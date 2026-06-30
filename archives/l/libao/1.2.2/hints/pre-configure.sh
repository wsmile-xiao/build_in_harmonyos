#!/bin/sh
# 生成 configure 脚本
# libao 源码中没有预生成的 configure 脚本，需要运行 autoreconf

if [ -f configure.ac ] && [ ! -f configure ]; then
    export PATH="/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH"
    autoreconf -isf
fi
