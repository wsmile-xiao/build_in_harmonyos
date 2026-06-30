#!/bin/bash
# HarmonyOS Perl XS 模块编译参数
# 构建系统: perl_xs (Makefile.PL)

# configure 阶段参数
export PERL_MAKEFILE_PL_OPTS="PREFIX=$DEFAULT_PREFIX"

# make 阶段参数
export CCFLAGS="-D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -I$DEFAULT_PREFIX/include"
export LDFLAGS="-L$DEFAULT_PREFIX/lib"
export LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc"

# 注意: 当 Perl 是静态链接(useshrplib=false)时，不需要添加 -lperl
