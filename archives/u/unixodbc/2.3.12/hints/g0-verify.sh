#!/bin/sh
# g0-verify.sh for unixodbc 2.3.12
# Manual clean-build smoke for the release-tarball path used by conanfile.py.

set -e

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

echo "=== G0 Verify for unixodbc 2.3.12 ==="

sh "$SCRIPT_DIR/pre-build.sh"

echo "=== Running configure ==="
./configure \
    --sysconfdir=/etc \
    --disable-gui \
    --disable-drivers \
    --disable-driver-config \
    --disable-readline \
    --disable-editline \
    --disable-stats \
    --disable-iconv \
    --enable-threads

echo "=== Running make ==="
make -j1

echo "=== Running make check ==="
make -j1 check

echo "=== Verifying products ==="
test -f DriverManager/.libs/libodbc.so.2.0.0
test -f odbcinst/.libs/libodbcinst.so.2.0.0
test -f cur/.libs/libodbccr.so.2.0.0
test -f exe/odbc_config
test -f exe/isql
test -f exe/odbcinst

exe/odbc_config --version
exe/odbc_config --ulen
exe/isql --version
exe/odbcinst --version

echo "=== G0 Verify PASSED ==="
