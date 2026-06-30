#!/bin/bash
# b2sum 20190724 编译指导脚本
# 构建系统：纯 Makefile（非 autotools）
# 源码嵌套：b2sum 子目录在 BLAKE2 仓库根目录内
# 依赖：无额外依赖（仅 libc）
# 注意：aarch64 不支持 SSE，必须使用 ref/ 纯 C 实现

# 补丁修改了 makefile（4处）：CFLAGS默认值、-I路径 ../sse→../ref、FILES源文件、链接行加 LDFLAGS
# 由于 build_subdir=b2sum，补丁从 b2sum/ 子目录内应用（-p1 作用在子目录层级）

cd b2sum/

make CC=clang \
    LDFLAGS='-fuse-ld=/data/service/hnp/bin/ld.bfd' \
    NO_OPENMP=1 \
    PREFIX=$DEFAULT_PREFIX \
    MANDIR=$DEFAULT_PREFIX/share/man \
    -j1