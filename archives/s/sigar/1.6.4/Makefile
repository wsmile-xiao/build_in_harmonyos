# sigar 1.6.4 — hand-written Makefile for the HarmonyOS/Linux C library build.
#
# The upstream 1.6.4 release tag ships only the C sources + headers (no
# autotools/CMake scaffolding, which lives only in the project's dev branch).
# This Makefile reproduces the library build of that dev build:
#   platform-independent src/*.c  +  src/os/linux/linux_sigar.c  =>  libsigar.a
# and installs the public headers.
#
# It also builds and runs the OFFICIAL upstream test programs (tests/*.c
# vendored from the hyperic/sigar project), matching the upstream autotools
# `make check` (check_PROGRAMS/TESTS).  See test_package/MANIFEST.yml audit.

CC      ?= clang
AR      ?= ar
RANLIB  ?= ranlib
PYTHON  ?= python3
SHELL   := /bin/sh

PREFIX  ?= /usr/local
DESTDIR ?=
LIBDIR  = $(DESTDIR)$(PREFIX)/lib
INCDIR  = $(DESTDIR)$(PREFIX)/include

# -fgnu89-inline reproduces the 2010-era semantics the upstream code relies on:
# its SIGAR_INLINE helpers (sigar_skip_token & friends) are declared `inline`
# (no static/extern) and referenced from other translation units. Modern
# compilers (default gnu17/gnu11) no longer emit external symbols for such
# functions, so -fgnu89-inline is required to avoid undefined references.
# -DSIGAR_NO_RPC disables the RPC (#include <rpc/rpc.h>) implementation, which
# needs libtirpc and is not available on HarmonyOS/musl; stubs are supplied by
# patches/0001.  -D_GNU_SOURCE exposes major()/minor() from <sys/sysmacros.h>
# (patches/0002).  -DSIGAR_NO_RINDEX maps the BSD legacy rindex() to the
# standard strrchr() (patches/0006): glibc exports rindex from <string.h> but
# musl (HarmonyOS) does not.
CPPFLAGS = -Iinclude -Isrc/os/linux -Itests
# The OHOS Conan buildenv injects CFLAGS (e.g. "-fPIC -O2") into the make
# environment.  A plain `CFLAGS ?=` would then be a no-op and the critical
# portability defines below (SIGAR_NO_GETPASS / SIGAR_NO_RPC / SIGAR_NO_RINDEX /
# -fgnu89-inline) would be silently dropped, producing the CI error:
#   sigar.c:2284: call to undeclared function 'getpass' / -Wint-conversion
# We use `override` so these required flags are always present even when the
# host/CI buildenv provides a CFLAGS of its own.
override CFLAGS := -O2 -fPIC -fgnu89-inline -D_GNU_SOURCE -DSIGAR_NO_RPC -DSIGAR_NO_GETPASS -DSIGAR_NO_RINDEX
override CFLAGS += $(CPPFLAGS)

# The upstream test programs are compiled with the same platform macro the
# upstream build sets on Linux (configure.ac AC_DEFINE(SIGAR_TEST_OS_LINUX) /
# tests/CMakeLists.txt ADD_DEFINITIONS(-DSIGAR_TEST_OS_LINUX)).  It gates
# assertions that do not apply to Linux (e.g. t_sigar_netif's `speed` field,
# which the Linux driver always reports as SIGAR_FIELD_NOTIMPL).
TEST_CPPFLAGS = -DSIGAR_TEST_OS_LINUX

LIB_SRCS = \
	src/sigar.c \
	src/sigar_cache.c \
	src/sigar_fileinfo.c \
	src/sigar_format.c \
	src/sigar_getline.c \
	src/sigar_ptql.c \
	src/sigar_signal.c \
	src/sigar_util.c \
	src/sigar_version.c \
	src/os/linux/linux_sigar.c

LIB_OBJS = $(patsubst src/%.c,%.o,$(patsubst src/os/linux/%.c,%.o,$(LIB_SRCS)))

TEST_PROGS = $(patsubst tests/%.c,%,$(wildcard tests/t_sigar_*.c))

.PHONY: all lib tests check install clean

all: lib

lib: libsigar.a

src/sigar_version.c: src/sigar_version.c.in gen_version.py
	$(PYTHON) gen_version.py

sigar.o: src/sigar.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar.c -o $@
sigar_cache.o: src/sigar_cache.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_cache.c -o $@
sigar_fileinfo.o: src/sigar_fileinfo.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_fileinfo.c -o $@
sigar_format.o: src/sigar_format.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_format.c -o $@
sigar_getline.o: src/sigar_getline.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_getline.c -o $@
sigar_ptql.o: src/sigar_ptql.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_ptql.c -o $@
sigar_signal.o: src/sigar_signal.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_signal.c -o $@
sigar_util.o: src/sigar_util.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_util.c -o $@
sigar_version.o: src/sigar_version.c
	$(CC) $(CFLAGS) -c src/sigar_version.c -o $@
linux_sigar.o: src/os/linux/linux_sigar.c src/sigar_version.c
	$(CC) $(CFLAGS) -c src/os/linux/linux_sigar.c -o $@

libsigar.a: $(LIB_OBJS)
	$(AR) rcs $@ $(LIB_OBJS)
	$(RANLIB) $@

# ---- upstream test programs (from hyperic/sigar tests/) ----
tests: $(TEST_PROGS)

$(TEST_PROGS): %: tests/%.c libsigar.a
	$(CC) $(CFLAGS) $(TEST_CPPFLAGS) tests/$@.c libsigar.a -o $@ -lm -ldl -lpthread

# run every upstream test program; fail if any exits non-zero
check: tests
	@mkdir -p check-logs; fail=0; run=0; for t in $(TEST_PROGS); do \
		run=$$((run+1)); \
		./$$t > check-logs/$$t.log 2>&1; \
		rc=$$?; \
		if [ $$rc -ne 0 ]; then \
			echo "TEST-FAIL: $$t rc=$$rc"; \
			fail=$$((fail+1)); \
		else \
			echo "TEST-PASS: $$t"; \
		fi; \
	done; \
	echo "sigar make check: executed=$$run failed=$$fail"; \
	if [ "$$fail" -ne 0 ]; then exit 1; fi

install: lib
	install -d $(LIBDIR) $(INCDIR)
	install -m 644 libsigar.a $(LIBDIR)/libsigar.a
	install -m 644 include/sigar.h $(INCDIR)/sigar.h
	install -m 644 include/sigar_fileinfo.h $(INCDIR)/sigar_fileinfo.h
	install -m 644 include/sigar_format.h $(INCDIR)/sigar_format.h
	install -m 644 include/sigar_getline.h $(INCDIR)/sigar_getline.h
	install -m 644 include/sigar_log.h $(INCDIR)/sigar_log.h
	install -m 644 include/sigar_private.h $(INCDIR)/sigar_private.h
	install -m 644 include/sigar_ptql.h $(INCDIR)/sigar_ptql.h
	install -m 644 include/sigar_util.h $(INCDIR)/sigar_util.h

clean:
	rm -f $(LIB_OBJS) libsigar.a $(TEST_PROGS)
