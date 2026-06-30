#!/bin/sh
# Touch autotools timestamp files to prevent make from trying to regenerate them
# This is needed after applying configure.ac/configure patches because
# the Makefile detects the changes and tries to run aclocal/autoconf/automake
# which may not be available or properly configured on OpenHarmony.

touch aclocal.m4 Makefile.in configure config.h.in stamp-h1 2>/dev/null
echo "Timestamps touched to prevent autotools regeneration"