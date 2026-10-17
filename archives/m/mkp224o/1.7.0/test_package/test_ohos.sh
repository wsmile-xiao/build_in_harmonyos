#!/usr/bin/env bash
# test_package/test_ohos.sh — OHOS-specific hard requirements for the
# final packaged mkp224o binary. All checks fail closed.
#
#  1. ELF64 AArch64
#  2. PT_INTERP == /lib/ld-musl-aarch64.so.1
#  3. exactly one .codesign section (binary-sign-tool)
#  4. no RPATH/RUNPATH, no host absolute paths in the binary
#  5. real run of threads + random source + ed25519 generation flow
#     (2-thread search with 1-char prefix, timed)
#  6. cleanup of generated key material
set -euo pipefail

BIN="$1"
READELF="${READELF:-llvm-readelf}"
command -v "$READELF" >/dev/null 2>&1 || READELF=readelf

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -x "$BIN" ] || fail "binary not executable: $BIN"

echo "[ohos] ELF class / machine"
HDR="$("$READELF" -h "$BIN")"
grep -q "Class:.*ELF64" <<<"$HDR" || fail "not ELF64"
grep -q "Machine:.*AArch64" <<<"$HDR" || fail "not AArch64"
echo "OK: ELF64 AArch64"

echo "[ohos] program interpreter"
# readelf prints the interpreter on the section-descriptor line under
# LOAD/INTERP; parsing that across tool variants is brittle — take the
# exact DT interp string from the binary instead.
# strings runs standalone so a real failure aborts (fail closed); only
# grep's expected no-match is caught by || true. Output is reused for
# the host-paths check below.
ALLSTR="$(strings -a "$BIN")"
INTERP="$(grep -m1 '^/lib/.*\.so\.1$' <<<"$ALLSTR" || true)"
[ "$INTERP" = "/lib/ld-musl-aarch64.so.1" ] \
    || fail "PT_INTERP is '$INTERP', expected /lib/ld-musl-aarch64.so.1"
# cross-check with readelf program headers (here-string, not a pipe, so
# pipefail cannot misfire on early-exiting grep)
PHDRS="$("$READELF" -l "$BIN")"
grep -q "Requesting program interpreter: /lib/ld-musl-aarch64.so.1" <<<"$PHDRS" \
    || fail "readelf INTERP request line mismatch"
echo "OK: interpreter $INTERP"

echo "[ohos] .codesign section"
SECS="$("$READELF" -SW "$BIN")"
NCS="$(grep -c '\.codesign' <<<"$SECS" || true)"
[ "$NCS" -eq 1 ] || fail ".codesign section count = $NCS, expected 1"
echo "OK: .codesign present (1)"

echo "[ohos] RPATH/RUNPATH"
DYN="$("$READELF" -d "$BIN")"
# expected-no-match grep: no match (exit 1) is the PASSING case; the
# && list keeps set -e off it, a match runs fail()
grep -qE '\b(RPATH|RUNPATH)\b' <<<"$DYN" \
    && fail "binary has RPATH/RUNPATH"
echo "OK: no RPATH/RUNPATH"

echo "[ohos] no host absolute paths in binary"
BADPATHS="$(grep -E '^(/storage/|/home/|/data/service/hnp|/build/)' <<<"$ALLSTR" || true)"
[ -z "$BADPATHS" ] || { head -5 <<<"$BADPATHS" >&2; fail "host absolute paths embedded in binary"; }
echo "OK: no host absolute paths"

echo "[ohos] real run: threads + randombytes + ed25519 (2 threads)"
OUTDIR="$(mktemp -d "${TMPDIR:-/tmp}/mkp224o-ohos.XXXXXX")"
# clean up key material on success, failure (set -e) AND signals
trap 'rm -rf "$OUTDIR"' EXIT HUP INT TERM
# 2 threads exercise the pthread worker pool; -n 1 stops after first hit;
# statistics line proves the batch/ed25519 loop actually ran.
timeout 120 "$BIN" -n 1 -t 2 -s -d "$OUTDIR" a >/dev/null 2>&1 \
    || fail "threaded key generation run failed or timed out"
KEYDIRS="$(find "$OUTDIR" -mindepth 1 -maxdepth 1 -type d)"
[ -n "$KEYDIRS" ] || fail "no key directory produced by threaded run"
# no `find | head -1` pipe: under pipefail a multi-directory find dies
# with SIGPIPE (141); head -n1 on a here-string keeps first-dir semantics
KEYDIR="$(head -n1 <<<"$KEYDIRS")"
for f in hostname hs_ed25519_public_key hs_ed25519_secret_key; do
    [ -f "$KEYDIR/$f" ] || fail "missing $f in threaded run output"
done
echo "OK: threaded generation produced complete key set"

echo "[ohos] cleanup"
rm -rf "$OUTDIR"
[ ! -d "$OUTDIR" ] || fail "cleanup failed"
echo "OK: cleaned up"

echo "ALL OHOS TESTS PASSED"
