#!/data/service/hnp/bin/bash
# test_md5deep.sh — functional test for the md5deep/hashdeep tool family.
# Verifies each tool computes the correct digest for a known input.
# Argument $1: directory containing the installed binaries (bin/).
set -euo pipefail

BINDIR="$1"
if [ -z "${BINDIR:-}" ] || [ ! -d "$BINDIR" ]; then
    echo "ERROR: binary dir not provided or missing: $BINDIR"
    exit 1
fi

WORK="$(pwd)/md5deep-testdata"
rm -rf "$WORK" && mkdir -p "$WORK"
DATA="$WORK/hello.txt"
printf 'hello\n' > "$DATA"

# Reference digests of the 6-byte string "hello\n".
MD5_EXPECT="b1946ac92492d2347c6235b4d2611184"
SHA1_EXPECT="f572d396fae9206628714fb2ce00f72e94f2258f"
SHA256_EXPECT="5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"

check() {
    local tool="$1" expect="$2"
    local out
    out="$("$BINDIR/$tool" "$DATA")"
    if echo "$out" | grep -qi "$expect"; then
        echo "PASS: $tool -> $expect"
    else
        echo "FAIL: $tool expected $expect, got: $out"
        exit 1
    fi
}

check md5deep    "$MD5_EXPECT"
check sha1deep   "$SHA1_EXPECT"
check sha256deep "$SHA256_EXPECT"

# hashdeep computes md5+sha256 by default; verify it emits the md5.
hd_out="$("$BINDIR/hashdeep" "$DATA")"
if echo "$hd_out" | grep -qi "$MD5_EXPECT"; then
    echo "PASS: hashdeep -> $MD5_EXPECT"
else
    echo "FAIL: hashdeep missing $MD5_EXPECT, got: $hd_out"
    exit 1
fi

# Sanity-check the reported version (-v prints the bare version string).
if "$BINDIR/md5deep" -v 2>&1 | grep -q "4.4"; then
    echo "PASS: md5deep version 4.4"
else
    echo "FAIL: unexpected md5deep version: $("$BINDIR/md5deep" -v 2>&1)"
    exit 1
fi

echo "ALL TESTS PASSED"
