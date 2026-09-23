#!/bin/sh
# test_package/test_bsdtar.sh — functional test for libarchive-tools binaries.
# Runs inside the conanrun env (PATH includes the installed bin/).
# 5 real assertions; every artifact is checked non-empty before comparison
# (an empty-vs-empty cmp would fake a pass).
# POSIX sh (HMBS shell_getcwd: /bin/sh); no bashisms.
set -eu

# Test 1: bsdtar executes and reports the packaged version
echo "[test] bsdtar --version"
bsdtar --version 2>&1 | tee bsdtar-version.txt
grep -qi "bsdtar" bsdtar-version.txt || {
    echo "FAIL: bsdtar --version did not report bsdtar"
    exit 1
}
grep -q "3.8.8" bsdtar-version.txt || {
    echo "FAIL: bsdtar --version did not report 3.8.8"
    exit 1
}
echo "PASS: bsdtar --version OK"

# Test 2: bsdcpio executes and reports itself
echo "[test] bsdcpio --version"
bsdcpio --version 2>&1 | tee bsdcpio-version.txt
grep -qi "cpio" bsdcpio-version.txt || {
    echo "FAIL: bsdcpio --version did not report cpio"
    exit 1
}
echo "PASS: bsdcpio --version OK"

# NOTE: /tmp is read-only on OHOS -- prefer HMBS-injected writable tmp.
# Probe TMPDIR/TMP/TEMP plus the HMBS fallback path (aldo precedent);
# fall back to the current directory, never to hard-coded /tmp.
SCRATCH=""
for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${HMBS_AUTOCONF_MKTEMP_FALLBACK:-}"; do
    case "$_cand" in
        ""|"0"|"1") continue ;;
        /tmp|/tmp/*) continue ;;
    esac
    if [ -d "$_cand" ]; then SCRATCH="$_cand"; break; fi
done
[ -n "$SCRATCH" ] || SCRATCH="$PWD"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/bsdtar-test-$$"
mkdir -p "$TESTDIR/src" "$TESTDIR/out"
trap 'rm -rf "$TESTDIR"' EXIT

# Deterministic payload: compressible text + byte dump, must be non-empty.
{
    seq 1 400 | sed 's/^/bsdtar round-trip line /'
    head -c 2048 /dev/urandom 2>/dev/null | od -An -tx1 | tr -d ' \n'
    echo
} > "$TESTDIR/src/payload.txt" 2>/dev/null || true
wc -c < "$TESTDIR/src/payload.txt" | grep -q '[1-9]' || {
    echo "FAIL: failed to create test input"
    exit 1
}
echo "hello bsdcat" > "$TESTDIR/src/greeting.txt"

# Test 3: create a tar archive (must be non-empty)
echo "[test] bsdtar -cf (create)"
bsdtar -cf "$TESTDIR/sample.tar" -C "$TESTDIR/src" payload.txt greeting.txt
test -s "$TESTDIR/sample.tar" || {
    echo "FAIL: bsdtar did not produce a non-empty archive"
    exit 1
}
echo "PASS: archive created ($(wc -c < "$TESTDIR/sample.tar") bytes)"

# Test 4: list the archive (output must name both members)
echo "[test] bsdtar -tf (list)"
bsdtar -tf "$TESTDIR/sample.tar" > "$TESTDIR/listing.txt"
test -s "$TESTDIR/listing.txt" || {
    echo "FAIL: bsdtar -tf produced empty listing"
    exit 1
}
grep -q "payload.txt" "$TESTDIR/listing.txt" || {
    echo "FAIL: listing misses payload.txt"
    exit 1
}
grep -q "greeting.txt" "$TESTDIR/listing.txt" || {
    echo "FAIL: listing misses greeting.txt"
    exit 1
}
echo "PASS: listing contains both members"

# Test 5: extract and byte-compare (extracted files must be non-empty too)
echo "[test] bsdtar -xf (extract) + cmp"
bsdtar -xf "$TESTDIR/sample.tar" -C "$TESTDIR/out"
test -s "$TESTDIR/out/payload.txt" || {
    echo "FAIL: extracted payload.txt is empty"
    exit 1
}
cmp -s "$TESTDIR/src/payload.txt" "$TESTDIR/out/payload.txt" || {
    echo "FAIL: extracted payload.txt differs from original"
    exit 1
}
cmp -s "$TESTDIR/src/greeting.txt" "$TESTDIR/out/greeting.txt" || {
    echo "FAIL: extracted greeting.txt differs from original"
    exit 1
}
echo "PASS: round-trip content identical"
