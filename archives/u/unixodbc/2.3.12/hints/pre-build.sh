#!/bin/sh
# pre-build.sh for unixodbc 2.3.12
# E011 workaround: autoreconf + umask fix for HMDFS
#
# Problem: GitHub API tarball has no configure script, and autoreconf generates
# configure with umask 077 which fails on HMDFS due to UID mapping.
#
# Solution: 
# 1. Run autoreconf to generate configure
# 2. Fix umask 077 → 022 in both configure and libltdl/configure

set -e

echo "=== pre-build.sh: Generating configure with autoreconf ==="

# Step 1: Generate configure script
autoreconf -fi

# Step 2: Fix umask 077 → 022 (E011 workaround)
# This allows group write permissions, which HMDFS UID mapping requires
echo "=== Fixing umask 077 → 022 in configure ==="
sed -i 's/umask 077/umask 022/g' configure

# Step 3: Fix umask in libltdl/configure if it exists
if [ -f libltdl/configure ]; then
    echo "=== Fixing umask 077 → 022 in libltdl/configure ==="
    sed -i 's/umask 077/umask 022/g' libltdl/configure
fi

echo "=== pre-build.sh completed ==="