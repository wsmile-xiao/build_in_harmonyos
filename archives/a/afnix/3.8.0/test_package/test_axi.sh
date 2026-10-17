#!/bin/sh
# test_package/test_axi.sh — R34: substantive afnix interpreter test
# (L0c accepts .sh as a test source file; this script mirrors the
# assertions in conanfile.py test() so CI L0c/L0d see a real test
# source file.)
#
# afnix ships the axi interpreter; this script runs axi -h (sanity)
# and then executes the upstream-style test.als against the installed
# axi — substantively depending on the packaged binaries, not a stub print.
set -eu

# Locate the installed axi binary from the conan dep's bin dir
AXI=""
for d in "$HOME/.conan2/p"/b/*/p/bin "$CONAN_INSTALL_ROOT"/bin; do
    if [ -x "$d/axi" ]; then
        AXI="$d/axi"
        break
    fi
done

if [ -z "$AXI" ]; then
    echo "FAIL: axi interpreter not found in conan dep bin/" >&2
    exit 1
fi

echo "OK: axi found at $AXI"

# Sanity: axi prints usage with -h (exit 0)
"$AXI" -h >/dev/null 2>&1 || {
    echo "FAIL: axi -h did not exit 0" >&2
    exit 1
}
echo "OK: axi -h sanity passed"

# Execute the upstream-style test.als (lives next to this script)
TEST_ALS="$(dirname "$0")/test.als"
if [ ! -f "$TEST_ALS" ]; then
    echo "FAIL: test.als missing next to test_axi.sh" >&2
    exit 1
fi
"$AXI" "$TEST_ALS" || {
    echo "FAIL: axi test.als did not pass" >&2
    exit 1
}
echo "afnix axi interpreter test OK: axi -h + test.als passed"
