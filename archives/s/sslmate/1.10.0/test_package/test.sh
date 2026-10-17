#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the sslmate package.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `sslmate`).
#
# The sslmate binary requires URI::Escape and Term::ReadKey (CPAN modules)
# which may not be available on all OHOS environments. This test verifies
# the package by loading the SSLMate Perl module (from the package's perllib/)
# and checking the version, and by confirming the binary is present.
set -euo pipefail

SSLMATE="${1:-sslmate}"

echo "[step] Locate sslmate binary"
# Find the actual path of sslmate (from PATH or direct)
SSLMATE_PATH=$(command -v "$SSLMATE" 2>/dev/null || echo "$SSLMATE")
if [ ! -f "$SSLMATE_PATH" ]; then
    echo "        [fail] sslmate binary not found: $SSLMATE_PATH"
    exit 1
fi
echo "        [ok] Found sslmate at: $SSLMATE_PATH"

echo "[step] Verify SSLMate module and version"
# The sslmate binary's perllib is at ../perllib relative to the binary
PERLLIB_DIR="$(dirname "$SSLMATE_PATH")/../perllib"
if [ ! -d "$PERLLIB_DIR" ]; then
    echo "        [fail] perllib directory not found: $PERLLIB_DIR"
    exit 1
fi

# Load the SSLMate module from the package's perllib and verify version.
# SSLMate.pm is a pure Perl module with no external CPAN dependencies.
output=$(perl -I "$PERLLIB_DIR" -e 'use SSLMate; print $SSLMate::VERSION, "\n"' 2>&1)
if echo "$output" | grep -q "1.10.0"; then
    echo "        [ok] SSLMate module loaded, version: $output"
else
    echo "        [fail] Version mismatch or module load error: $output"
    exit 1
fi

echo "[step] Verify sslmate script integrity"
# Verify the sslmate script is a valid Perl script
if head -1 "$SSLMATE_PATH" | grep -q "perl"; then
    echo "        [ok] sslmate is a Perl script"
else
    echo "        [fail] sslmate is not a Perl script"
    exit 1
fi

echo "sslmate test_package: PASS"
