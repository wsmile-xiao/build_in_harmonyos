#!/bin/bash
# test_package/test_ccr.sh — functional test for the packaged ccr binary.
#
# codecrypt upstream ships NO test suite (v1.8 tarball has no tests/ dir,
# Makefile.am registers no TESTS; see notes.md), so this consumer-side test
# exercises the real binary end-to-end (R34):
#   1. ccr -V prints "codecrypt 1.8"
#   2. ccr -g help lists the full algorithm suite incl. cryptopp-backed
#      variants (MCEQCMDPC*/FMTSEQ* + ARCFOUR/CHACHA20/XSYND + hashes)
#   3. symmetric key gen (SYM = CHACHA20,CUBE512) + encrypt + decrypt
#      round-trip: plaintext comes back identical
# Asymmetric keygen takes minutes (Merkle trees) so the symmetric path is
# used; CCR_RANDOM_SEED=/dev/urandom avoids blocking on /dev/random.
set -euo pipefail

CCR="$1"
TMPDIR_T="$2"
mkdir -p "$TMPDIR_T"
KEY="$TMPDIR_T/sym.key"
ENC="$TMPDIR_T/msg.enc"
PLAINTEXT="codecrypt OHOS symmetric roundtrip test 12345"
export CCR_RANDOM_SEED=/dev/urandom
export CCR_HOME="$TMPDIR_T"

echo "== 1/3 version =="
OUT="$("$CCR" -V 2>&1)"
echo "$OUT" | head -1
case "$OUT" in
    *"codecrypt 1.8"*) echo "ok   : version matches" ;;
    *) echo "FAIL : unexpected -V output: $OUT"; exit 1 ;;
esac

echo "== 2/3 algorithm suite =="
OUT="$("$CCR" -g help 2>&1)"
for ALG in MCEQCMDPC128FO-CUBE256-ARCFOUR MCEQCMDPC128FO-SHA256-ARCFOUR \
           FMTSEQ128C-CUBE256-CUBE128 FMTSEQ128C-SHA256-RIPEMD128 \
           CHACHA20 XSYND SHA512 CUBE512; do
    case "$OUT" in
        *"$ALG"*) echo "ok   : $ALG registered" ;;
        *) echo "FAIL : algorithm $ALG missing from suite"; exit 1 ;;
    esac
done

echo "== 3/3 symmetric roundtrip =="
"$CCR" -S "$KEY" -g SYM >/dev/null 2>&1 || {
    echo "FAIL : symkey generation failed"; exit 1; }
[ -f "$KEY" ] || { echo "FAIL : symkey file missing"; exit 1; }
printf '%s\n' "$PLAINTEXT" | "$CCR" -S "$KEY" -e -o "$ENC" >/dev/null 2>&1 || {
    echo "FAIL : symmetric encryption failed"; exit 1; }
OUT="$("$CCR" -S "$KEY" -d -R "$ENC" 2>/dev/null)" || {
    echo "FAIL : symmetric decryption failed"; exit 1; }
case "$OUT" in
    *"$PLAINTEXT"*) echo "ok   : roundtrip OK" ;;
    *) echo "FAIL : roundtrip mismatch: got $OUT"; exit 1 ;;
esac

echo "codecrypt test_package: ALL OK"
