#!/bin/sh
# Pre-build script for OpenHarmony
# This script creates necessary files for building on HMDFS

# Create Makefile
cat > Makefile << 'EOF'
# Makefile for libresample
# Generated manually for OpenHarmony

CC = gcc
CFLAGS = -g -O2
LDFLAGS =
LIBS = -lm
AR = ar
RANLIB = ranlib
srcdir = .

OBJS = \
	src/resample.c.o \
	src/resamplesubs.c.o \
	src/filterkit.c.o

TARGETS = libresample.a tests/testresample
DIRS=tests

all: $(TARGETS)

libresample.a: $(OBJS) Makefile
	$(AR) ruv libresample.a $(OBJS)
	ranlib libresample.a

tests/testresample: libresample.a $(srcdir)/tests/testresample.c
	$(CC) -o tests/testresample \
		$(CFLAGS) $(LDFLAGS)  $(srcdir)/tests/testresample.c \
		libresample.a $(LIBS)

tests/compareresample: libresample.a $(srcdir)/tests/compareresample.c
	$(CC) -o tests/compareresample \
		$(CFLAGS) $(LDFLAGS) $(srcdir)/tests/compareresample.c \
		libresample.a -lsamplerate $(LIBS)

tests/resample-sndfile: libresample.a $(srcdir)/tests/resample-sndfile.c
	$(CC) -o tests/resample-sndfile \
		$(CFLAGS) $(LDFLAGS) $(srcdir)/tests/resample-sndfile.c \
		libresample.a -lsndfile $(LIBS)

$(DIRS):
	mkdir $(DIRS)

clean:
	rm -f $(TARGETS) $(OBJS)

distclean: clean
	rm -f Makefile
	rm -f config.status config.cache config.log src/config.h
	rm -f *~ src/*~ tests/*~ include/*~

$(OBJS): %.c.o: $(srcdir)/%.c Makefile $(srcdir)/include/libresample.h \
	$(srcdir)/src/resample_defs.h $(srcdir)/src/filterkit.h $(srcdir)/src/config.h
	$(CC) -c $(CFLAGS) $< -o $@
EOF

# Create config.h
mkdir -p src
cat > src/config.h << 'EOF'
/* config.h - Generated manually for OpenHarmony */
#ifndef CONFIG_H
#define CONFIG_H

#define HAVE_INTTYPES_H 1

#endif /* CONFIG_H */
EOF

echo "Pre-build script completed"