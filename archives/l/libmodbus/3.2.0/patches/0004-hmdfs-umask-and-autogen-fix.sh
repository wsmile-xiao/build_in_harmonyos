#!/bin/sh
# Pre-configure script for libmodbus 3.1.12 on HMDFS
# 1. Generate configure from configure.ac (GitHub tarball doesn't include it)
autoreconf --install --force
# 2. HMDFS umask trap: fix umask 000 to umask 007 in configure
sed -i 's/umask 000 && mktemp/umask 007 \&\& mktemp/g' configure
sed -i 's/umask 000 && mkdir/umask 007 \&\& mkdir/g' configure