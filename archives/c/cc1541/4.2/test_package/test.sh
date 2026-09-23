#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the cc1541 4.2 executable.
# Runs in conanrun env (PATH includes <package>/bin). All artifacts are
# created inside a scratch directory so the recipe tree stays clean
# (/tmp on OHOS is read-only; TMPDIR points to a writable location).
set -euo pipefail

WORK="${TMPDIR:-$(pwd)}/cc1541_test_package_$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'rm -rf "$WORK"' EXIT

# [1] The usage banner carries the real version string (bare invocation
# prints usage and exits non-zero).
banner="$(cc1541 2>&1 || true)"
echo "$banner" | grep -q "This is cc1541 version 4.2"
echo "assert 1 OK: version banner"

# [2] Real behavior: create a 35-track D64 image holding one PRG file
# (-w adds the local file; the image path is the last argument).
printf 'cc1541 consumer test payload\n' > hello.prg
cc1541 -w hello.prg test.d64
echo "assert 2 OK: image created"

# [3] A 35-track D64 image is 683 blocks x 256 bytes.
size="$(wc -c < test.d64 | tr -d '[:space:]')"
[ "$size" -eq 174848 ]
echo "assert 3 OK: image size $size"

# [4] The directory sector must contain the stored file name entry. cc1541
# stores the name PETSCII-encoded (lowercase ASCII input lands as uppercase
# bytes), so match case-insensitively: NUL-strip, upper-case, then match.
# Command substitution reads the whole file (no pipe race, no grep -a).
text="$(tr -d '\000' < test.d64 | tr '[:lower:]' '[:upper:]')"
case "$text" in
    *HELLO*) echo "assert 4 OK: directory entry found" ;;
    *) echo "assert 4 FAIL: directory entry missing"; exit 1 ;;
esac

echo "cc1541 consumer test: 4/4 assertions passed"
cd /
