#!/bin/sh
# After applying configure.ac patch, regenerate configure script
# Required because autoreconf -fi requires libtoolize which is not available
# on OpenHarmony. Running autoconf alone is sufficient since the other
# generated files (Makefile.in, config.h.in) are already in the tarball.

autoconf 2>/dev/null