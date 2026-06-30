#!/bin/sh
# g0-verify.sh for unixodbc 2.3.12
# G0 clean-build-verify with pre-build support
#
# Problem: GitHub tarball has no configure script
# Solution: Run autoreconf + E011 fix before configure

set -e

echo "=== G0 Verify for unixodbc 2.3.12 ==="

# Step 1: Check if configure exists
if [ ! -f configure ]; then
    echo "=== configure not found, running autoreconf ==="
    autoreconf -fi
fi

# Step 2: E011 fix (umask 077 → 022)
echo "=== Applying E011 fix ==="
sed -i 's/umask 077/umask 022/g' configure
if [ -f libltdl/configure ]; then
    sed -i 's/umask 077/umask 022/g' libltdl/configure
fi

# Step 3: Configure
echo "=== Running configure ==="
./configure --prefix=/storage/Users/currentUser/usr/local

# Step 4: Build
echo "=== Running make ==="
make -j1

# Step 5: Verify products
echo "=== Verifying products ==="
if [ -f DriverManager/.libs/libodbc.so.2.0.0 ]; then
    echo "✅ libodbc.so.2.0.0 exists ($(stat -c%s DriverManager/.libs/libodbc.so.2.0.0) bytes)"
else
    echo "❌ libodbc.so.2.0.0 missing"
    exit 1
fi

if [ -f exe/.libs/isql ]; then
    echo "✅ isql exists ($(stat -c%s exe/.libs/isql) bytes)"
else
    echo "❌ isql missing"
    exit 1
fi

echo "=== G0 Verify PASSED ==="
exit 0