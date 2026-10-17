#!/bin/sh
# test_package/test.sh — Consumer smoke test for perl-crypt-openssl-verify
# Tests: package structure, ELF validity, exported XS symbols, dynamic deps.
# On non-OHOS, also tests runtime module loading via perl.

set -eu

PKG_DIR="${1:-$(dirname "$0")/..}"

# --- Test 1: File presence ---
PM_FILE=$(find "$PKG_DIR" -name "Verify.pm" -type f 2>/dev/null | head -1)
if [ -z "$PM_FILE" ]; then
    echo "FAIL: Verify.pm not found in package"
    exit 1
fi
echo "OK: Found Verify.pm at $PM_FILE"

SO_FILE=$(find "$PKG_DIR" -name "Verify.so" -type f 2>/dev/null | head -1)
if [ -z "$SO_FILE" ]; then
    echo "FAIL: Verify.so not found in package"
    exit 1
fi
echo "OK: Found Verify.so at $SO_FILE"

# --- Test 2: ELF structure (must be valid ELF shared object) ---
if ! readelf -h "$SO_FILE" >/dev/null 2>&1; then
    echo "FAIL: $SO_FILE is not a valid ELF file"
    exit 1
fi
ELF_TYPE=$(readelf -h "$SO_FILE" 2>/dev/null | awk '/Type:/{print $2}')
echo "OK: ELF type: ${ELF_TYPE:-unknown}"

# --- Test 3: Exported symbols (must have Perl XS bootstrap symbol) ---
if ! nm -D "$SO_FILE" 2>/dev/null | grep -q "boot_Crypt__OpenSSL__Verify"; then
    echo "FAIL: boot_Crypt__OpenSSL__Verify symbol not found in $SO_FILE"
    exit 1
fi
echo "OK: boot_Crypt__OpenSSL__Verify symbol found"

# --- Test 4: Dynamic dependencies (should link against OpenSSL) ---
DYN_DEPS=$(readelf -d "$SO_FILE" 2>/dev/null | grep "NEEDED" || true)
echo "OK: Dynamic dependencies:"
echo "$DYN_DEPS"

# --- Test 5: Security flags (GNU_STACK should be RW = NX enabled) ---
if readelf -lW "$SO_FILE" 2>/dev/null | grep -q "GNU_STACK.*RW"; then
    echo "OK: GNU_STACK is RW (NX enabled)"
else
    echo "WARN: GNU_STACK not found or not RW"
fi

# --- Test 6: Runtime module loading (platform-dependent) ---
OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
if [ "$OS_NAME" = "OHOS" ]; then
    echo "INFO: OHOS - skipping runtime dlopen test (SELinux E073)"
elif command -v perl >/dev/null 2>&1; then
    PERL5LIB_DIR=$(dirname "$PM_FILE")
    if PERL5LIB="$PERL5LIB_DIR" perl -e 'require Crypt::OpenSSL::Verify; 1' 2>/dev/null; then
        echo "OK: Runtime module loading successful"
    else
        echo "FAIL: Runtime module loading failed - require Crypt::OpenSSL::Verify failed"
        exit 1
    fi
else
    echo "INFO: perl not available - skipping runtime test"
fi

echo "test perl-crypt-openssl-verify 0.36-r2: OK"
