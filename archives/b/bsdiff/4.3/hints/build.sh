#!/bin/bash
# bsdiff 4.3 编译指导脚本
# 构建系统：makefile（BSD风格）
# 依赖：bzip2 1.0.8

# 编译命令（不依赖 Makefile 的默认规则）
clang -O2 -Wall -fPIC -I$HOME/usr/local/include \
    -o bsdiff bsdiff.c \
    -L$HOME/usr/local/lib -lbz2 \
    -fuse-ld=bfd

clang -O2 -Wall -fPIC -I$HOME/usr/local/include \
    -o bspatch bspatch.c \
    -L$HOME/usr/local/lib -lbz2 \
    -fuse-ld=bfd
