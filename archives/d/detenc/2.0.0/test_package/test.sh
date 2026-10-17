#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the detenc executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] detenc -v reports version"
detenc -v | grep -q "detenc: version 2.0.0"
echo "OK: detenc -v => detenc: version 2.0.0"

# Sample files replicate upstream test/inputs (same bytes).
printf 'Hello world\n' > ascii.txt
printf 'H\xe2ll\xf6' > latin1.txt
printf '\xfe\xff\x00H\x00\xe2\x00l\x00l\x00\xf6' > utf16be.txt
printf '\xff\xfeH\x00\xe2\x00l\x00l\x00\xf6\x00' > utf16le.txt
printf '\xef\xbb\xbfH\xc3\xa2ll\xc3\xb6' > utf8bom.txt

check() {
    expected="$1"
    file="$2"
    got=$(detenc -q "$file")
    echo "[test] detenc -q $file => $got (expect $expected)"
    if [ "$got" != "$expected" ]; then
        echo "FAIL: expected $expected, got $got for $file"
        exit 1
    fi
}

check "US-ASCII" ascii.txt
check "ISO-8859-15" latin1.txt
check "UTF-16BE" utf16be.txt
check "UTF-16LE" utf16le.txt
check "UTF-8" utf8bom.txt

# Clean up sample files (test_package runs in-place inside the repo).
rm -f ascii.txt latin1.txt utf16be.txt utf16le.txt utf8bom.txt

echo "OK: all detenc 2.0.0 test_package assertions passed"
