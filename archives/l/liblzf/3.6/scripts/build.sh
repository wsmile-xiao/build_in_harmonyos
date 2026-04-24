#!/bin/bash
# liblzf 3.6 构建脚本
# 解决 config.status 临时文件创建失败问题（HMDFS 权限限制）

set -e

DEFAULT_PREFIX="${DEFAULT_PREFIX:-/storage/Users/currentUser/usr/local}"
TEST_PREFIX="${TEST_PREFIX:-/storage/Users/currentUser/tmp/test-install-liblzf-3.6}"
TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}"

SRC_DIR="${1:-$TMPDIR/builds/liblzf-3.6.orig}"
BUILD_DIR="$TMPDIR/liblzf-build"

# 创建构建目录
mkdir -p $BUILD_DIR
cd $BUILD_DIR

# 运行 configure（会失败，但生成 config.status）
$SRC_DIR/configure --prefix=$DEFAULT_PREFIX || true

# 手动创建 config.h 和 Makefile
# config.h - 基于 configure 的检测结果
cat > config.h << 'CONFIG_EOF'
/* config.h.  Generated from config.h.in by configure.  */

/* Define if you have the ANSI C header files.  */
#define STDC_HEADERS 1

/* The number of bytes in a int.  */
#define SIZEOF_INT 4

/* The number of bytes in a long.  */
#define SIZEOF_LONG 8

/* The number of bytes in a short.  */
#define SIZEOF_SHORT 2

/* Define to 1 if you have the <sys/types.h> header file.  */
#define HAVE_SYS_TYPES_H 1

/* Define to 1 if you have the <sys/stat.h> header file.  */
#define HAVE_SYS_STAT_H 1

/* Define to 1 if you have the <stdlib.h> header file.  */
#define HAVE_STDLIB_H 1

/* Define to 1 if you have the <string.h> header file.  */
#define HAVE_STRING_H 1

/* Define to 1 if you have the <memory.h> header file.  */
#define HAVE_MEMORY_H 1

/* Define to 1 if you have the <strings.h> header file.  */
#define HAVE_STRINGS_H 1

/* Define to 1 if you have the <inttypes.h> header file.  */
#define HAVE_INTTYPES_H 1

/* Define to 1 if you have the <stdint.h> header file.  */
#define HAVE_STDINT_H 1

/* Define to 1 if you have the <unistd.h> header file.  */
#define HAVE_UNISTD_H 1

/* Define to 1 if you have the <getopt.h> header file.  */
#define HAVE_GETOPT_H 1

/* Define to 1 if you have the `getopt_long' function.  */
#define HAVE_GETOPT_LONG 1

/* Enable GNU extensions  */
#define _GNU_SOURCE 1
CONFIG_EOF

# Makefile - 基于 Makefile.in，支持 VPATH
cat > Makefile << 'MAKE_EOF'
VERSION = 3.6

prefix = $DEFAULT_PREFIX
exec_prefix = $(prefix)
libdir = $(exec_prefix)/lib
bindir = $(exec_prefix)/bin
includedir = $(prefix)/include

VPATH = $SRC_DIR

CC = clang
CPPFLAGS = -I.
CFLAGS = -fPIC -O2
LDFLAGS = 
RANLIB = llvm-ranlib
AR = llvm-ar
INSTALL = /storage/Users/currentUser/usr/local/bin/install
INSTALL_DATA = $(INSTALL) -m 644

all: lzf

clean:
	-rm -f *.o *.a lzf bench

lzf_c.o: lzf_c.c lzfP.h

lzf_d.o: lzf_d.c lzfP.h

lzf.o: lzf.c

lzf: lzf.o liblzf.a

lzfP.h: lzf.h config.h

liblzf.a: lzf_c.o lzf_d.o
	rm -f $@
	$(AR) rc $@ $^
	$(RANLIB) $@

install: all
	$(INSTALL) -d $(bindir)
	$(INSTALL) -m 755 lzf $(bindir)
	$(INSTALL) -d $(includedir)
	$(INSTALL_DATA) lzf.h $(includedir)
	$(INSTALL) -d $(libdir)
	$(INSTALL_DATA) liblzf.a $(libdir)
MAKE_EOF

# 编译
make -j$(nproc)

echo "构建完成！"
echo "产物目录: $BUILD_DIR"
