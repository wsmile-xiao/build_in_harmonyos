#!/bin/sh
# test_rsa.sh — Test script for Crypt-OpenSSL-RSA package.
#
# R34: Substantive test that verifies the XS module build:
# 1. RSA.pm is syntactically valid Perl (perl -c)
# 2. RSA.so is a valid ELF shared object (file)
# 3. RSA.so contains the XS bootstrap function (readelf -s)
# 4. RSA.so links against OpenSSL libraries (readelf -d)
#
# Usage: test_rsa.sh <package_folder>
#
# Note: XS module runtime loading is blocked by SELinux HMDFS on HarmonyOS.
# This script uses static analysis instead of runtime API calls.

set -e

PKG_DIR="${1:?Usage: test_rsa.sh <package_folder>}"

# Detect Perl version and architecture dynamically
PERL_VER=$(perl -e 'print sprintf("%vd", $^V)')
PERL_ARCH=$(perl -MConfig -e 'print $Config{archname}')

# Fallbacks
: "${PERL_VER:=5.42.0}"
: "${PERL_ARCH:=aarch64-linux}"

echo "Perl version: $PERL_VER"
echo "Perl arch: $PERL_ARCH"

# Test 1: RSA.pm exists and is valid Perl
RSA_PM="$PKG_DIR/lib/site_perl/$PERL_VER/Crypt/OpenSSL/RSA.pm"
if [ ! -f "$RSA_PM" ]; then
    echo "FAIL: RSA.pm not found at $RSA_PM"
    exit 1
fi
echo "Checking RSA.pm syntax..."
perl -c "$RSA_PM"
echo "PASS: RSA.pm syntax OK"

# Test 2: RSA.so exists and is valid ELF
RSA_SO="$PKG_DIR/lib/site_perl/$PERL_VER/$PERL_ARCH/auto/Crypt/OpenSSL/RSA/RSA.so"
if [ ! -f "$RSA_SO" ]; then
    echo "FAIL: RSA.so not found at $RSA_SO"
    exit 1
fi
echo "Checking RSA.so file type..."
file "$RSA_SO" | grep -q "ELF"
echo "PASS: RSA.so is valid ELF"

# Test 3: RSA.so contains XS boot function
echo "Checking XS boot symbol..."
readelf -s "$RSA_SO" | grep -i "boot_Crypt"
echo "PASS: XS boot function present"

# Test 4: RSA.so links against OpenSSL
echo "Checking OpenSSL dependency..."
readelf -d "$RSA_SO" | grep -E "libssl|libcrypto"
echo "PASS: OpenSSL dependency verified"

echo ""
echo "=== All tests passed ==="
