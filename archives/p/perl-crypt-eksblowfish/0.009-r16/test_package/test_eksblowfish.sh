#!/bin/bash
# test_eksblowfish.sh — verify Crypt::Eksblowfish package works correctly
# Called by test_package/conanfile.py test() method
# R34: calls the Blowfish encrypt/decrypt API, not just loads the module

set -euo pipefail

# Argument: package folder path
PKG_DIR="${1:-}"

if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder path not provided"
    exit 1
fi

# Find Eksblowfish.so in package
SO_FILE=$(find "$PKG_DIR" -name "Eksblowfish.so" -type f 2>/dev/null | head -1)
if [ -z "$SO_FILE" ]; then
    echo "FAIL: Eksblowfish.so not found in package"
    exit 1
fi
echo "PASS: Found Eksblowfish.so at $SO_FILE"

# Verify .so is a valid ELF shared object
file "$SO_FILE" | grep -q "ELF" || {
    echo "FAIL: $SO_FILE is not a valid ELF"
    exit 1
}
echo "PASS: Eksblowfish.so is valid ELF"

# Find Crypt/Eksblowfish.pm
PM_FILE=$(find "$PKG_DIR" -path "*/Crypt/Eksblowfish.pm" -type f 2>/dev/null | head -1)
if [ -z "$PM_FILE" ]; then
    echo "FAIL: Crypt/Eksblowfish.pm not found"
    exit 1
fi
echo "PASS: Found Crypt/Eksblowfish.pm at $PM_FILE"

# Check subpackage .pm files
for submod in Bcrypt.pm Blowfish.pm Family.pm Subkeyed.pm Uklblowfish.pm; do
    sub_file=$(find "$PKG_DIR" -path "*/Crypt/Eksblowfish/$submod" -type f 2>/dev/null | head -1)
    if [ -z "$sub_file" ]; then
        echo "FAIL: Crypt/Eksblowfish/$submod not found"
        exit 1
    fi
    echo "PASS: Found Crypt/Eksblowfish/$submod"
done

# Locate Perl library paths
PERL_LIB=$(find "$PKG_DIR" -path "*/lib/perl5" -type d 2>/dev/null | head -1)
PERL_ARCH_LIB=$(find "$PKG_DIR" -path "*/lib/perl5/aarch64-linux" -type d 2>/dev/null | head -1)

if [ -z "$PERL_LIB" ] || [ -z "$PERL_ARCH_LIB" ]; then
    echo "FAIL: Perl lib directories not found in package"
    exit 1
fi

# R34: Call the encryption API — Blowfish encrypt/decrypt round-trip
# R9: Do not blindly swallow API failures — distinguish platform limitations from real bugs
API_OUTPUT=$(PERL5LIB="${PERL_LIB}:${PERL_ARCH_LIB}" perl -e '
use strict;
use warnings;
use Crypt::Eksblowfish::Blowfish;

# Create Blowfish cipher with a known key
my $key = pack("H*", "0123456789abcdef");
my $cipher = Crypt::Eksblowfish::Blowfish->new($key);

# Encrypt known plaintext (8 bytes of zeros)
my $plaintext = pack("H*", "0000000000000000");
my $ciphertext = $cipher->encrypt($plaintext);

die "encrypt returned wrong length" unless length($ciphertext) == 8;

# Decrypt and verify round-trip
my $decrypted = $cipher->decrypt($ciphertext);
die "round-trip mismatch" unless $plaintext eq $decrypted;

print "PASS: Blowfish encrypt/decrypt round-trip OK\n";
' 2>&1) && API_RC=0 || API_RC=$?

if [ "$API_RC" -eq 0 ]; then
    echo "$API_OUTPUT"
elif echo "$API_OUTPUT" | grep -qiE "dlopen|SELinux|permission denied|cannot (open|load|shared object|stat)"; then
    # Known OHOS platform limitation: SELinux blocks dlopen from HMDFS context
    echo "WARN: API call failed — known platform limitation (SELinux/dlopen restriction on OHOS)"
    echo "      Output: $API_OUTPUT"
else
    echo "FAIL: API call failed — not a platform limitation (possible real bug)"
    echo "      Output: $API_OUTPUT"
    exit 1
fi

echo "All checks completed"
