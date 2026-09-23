# Makefile for the topparser 1.3 library.
#
# Builds a small, dependency-free static library that parses the output of
# the Linux `top -b` command. Survives from the conan recipe via the
# standard CC/AR/CFLAGS CFLAGS environment plus a PREFIX install path.

CC      ?= cc
AR      ?= ar
CFLAGS  ?= -O2 -g
CFLAGS  += -std=c99 -Wall -Wextra -I.
ARFLAGS ?= rcs

LIB      = libtopparser.a
OBJS     = topparser.o
HDR      = topparser.h

PREFIX  ?= /usr/local

all: $(LIB)

$(LIB): $(OBJS)
	$(AR) $(ARFLAGS) $@ $^

topparser.o: topparser.c topparser.h
	$(CC) $(CFLAGS) -c topparser.c -o $@

# Upstream self-test suite (see tests/test_top.c).
# Builds and runs the C self-test binary against representative `top -b` snapshots.
tests/self : tests/test_top.c $(LIB)
	$(CC) $(CFLAGS) tests/test_top.c $(LIB) -lm -o $@

test: tests/self
	./tests/self

check: test

install: all
	install -d $(DESTDIR)$(PREFIX)/include $(DESTDIR)$(PREFIX)/lib
	install -m 644 $(HDR)    $(DESTDIR)$(PREFIX)/include/topparser.h
	install -m 644 $(LIB)    $(DESTDIR)$(PREFIX)/lib/$(LIB)

clean:
	rm -f $(OBJS) $(LIB) tests/self

.PHONY: all test check install clean
