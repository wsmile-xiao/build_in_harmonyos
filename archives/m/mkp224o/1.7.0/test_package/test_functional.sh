#!/usr/bin/env bash
# test_package/test_functional.sh — L1 consumer/functional test for the
# FINAL Conan package binary (mkp224o), run on OpenHarmony PC.
#
# Uses an extremely low difficulty (1-char prefix) legal filter so the
# search terminates quickly; hard timeout everywhere; fail closed.
#
# Verifies:
#   1. binary runs and prints version
#   2. output directory + hostname/public/secret key file structure
#   3. v3 onion address charset (a-z2-7), length (56 + ".onion" = 62)
#   4. hostname file content matches directory name
#   5. public/secret key sizes (32/64 bytes + prefixes)
#   6. cleans up all generated key material
set -euo pipefail

BIN="$1"

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -x "$BIN" ] || fail "mkp224o binary not executable: $BIN"

echo "[test] mkp224o -V (version)"
timeout 30 "$BIN" -V || fail "mkp224o -V exited non-zero"

OUTDIR="$(mktemp -d "${TMPDIR:-/tmp}/mkp224o-func.XXXXXX")"
# clean up key material on success, failure (set -e) AND signals
trap 'rm -rf "$OUTDIR"' EXIT HUP INT TERM

echo "[test] generating 1 key with 1-char prefix 'a' (low difficulty)"
# -n 1: stop after 1 key; -t 1: single thread; -d: output dir.
# Timeout 120s is generous: 1-char prefix = 1/32 odds per key on average.
timeout 120 "$BIN" -n 1 -t 1 -d "$OUTDIR" a >/dev/null 2>&1 \
    || fail "mkp224o address search failed or timed out"

echo "[test] verifying output structure"
KEYDIRS="$(find "$OUTDIR" -mindepth 1 -maxdepth 1 -type d)"
[ -n "$KEYDIRS" ] || fail "no key directory created under output dir"
NDIRS="$(echo "$KEYDIRS" | wc -l)"
[ "$NDIRS" -eq 1 ] || fail "expected exactly 1 key directory, got $NDIRS"

KEYDIR="$KEYDIRS"
DIRNAME="$(basename "$KEYDIR")"

echo "[test] hostname file"
HOSTNAME_FILE="$KEYDIR/hostname"
[ -f "$HOSTNAME_FILE" ] || fail "missing hostname file"
ADDR="$(cat "$HOSTNAME_FILE")"
# strip trailing newline
ADDR="${ADDR%$'\n'}"
echo "[test] onion address prefix: ${ADDR:0:8}[...] (full address not logged)"

echo "[test] address charset and length"
# v3 onion: 56 chars base32 (RFC 4648 alphabet a-z2-7, incl. l/o/v) + ".onion"
ADDR_BODY="${ADDR%.onion}"
[ "${#ADDR}" -eq 62 ] || fail "address length != 62: got ${#ADDR}"
[ "$ADDR_BODY.onion" = "$ADDR" ] || fail "address does not end in .onion"
case "$ADDR_BODY" in
    *[!a-z2-7]*) fail "address contains chars outside base32 alphabet a-z2-7" ;;
esac
echo "OK: address is 56-char base32 + .onion, valid charset"

echo "[test] directory name matches address"
[ "$DIRNAME" = "$ADDR" ] || fail "dir name != hostname content"

echo "[test] key files"
PUB="$KEYDIR/hs_ed25519_public_key"
SEC="$KEYDIR/hs_ed25519_secret_key"
[ -f "$PUB" ] || fail "missing hs_ed25519_public_key"
[ -f "$SEC" ] || fail "missing hs_ed25519_secret_key"
PUBSZ=$(stat -c %s "$PUB")
SECSZ=$(stat -c %s "$SEC")
# Tor v3 format (upstream common.h): public = 29+3 prefix + 32 key = 64;
# secret = 29+3 prefix + 64 key = 96.
[ "$PUBSZ" -eq 64 ] || fail "public key size $PUBSZ != 64"
[ "$SECSZ" -eq 96 ] || fail "secret key size $SECSZ != 96"
echo "OK: key file sizes correct (pub 64, secret 96)"

echo "[test] key file format (prefixes, checksum, version byte)"
# Full independent re-derivation of the onion address from the key
# files, per torspec proposal 224 and upstream worker.c/worker_batch.inc.h:
#   payload     = PK(32) || CHECKSUM(2) || VERSION(1)   (35 bytes)
#   CHECKSUM    = SHA3-256(".onion checksum" || PK || 0x03)[:2]
#   VERSION     = 0x03
#   address     = base32(payload) + ".onion"
# also verifies the "== ed25519v1-{public,secret}: type0 ==" file
# prefixes written by worker.c (29 chars + 3 NUL padding = 32).
python3 - "$PUB" "$SEC" "$ADDR_BODY" <<'EOF' || fail "key file format / v3 derivation check failed"
import base64, hashlib, sys
pubfile, secfile, addr = sys.argv[1], sys.argv[2], sys.argv[3]
pub = open(pubfile, "rb").read()
sec = open(secfile, "rb").read()

# 1. file prefixes (worker.c: pkprefix/skprefix, 29 chars + \0\0\0)
pkprefix = b"== ed25519v1-public: type0 ==" + b"\0" * 3
skprefix = b"== ed25519v1-secret: type0 ==" + b"\0" * 3
assert len(pub) == 64 and pub[:32] == pkprefix, "bad public key prefix/size"
assert len(sec) == 96 and sec[:32] == skprefix, "bad secret key prefix/size"

# 2. key material layout: last 32 bytes of pub = PK; last 64 of sec = SK
pk = pub[-32:]
sk = sec[-64:]

# 3. secret key format: mkp224o stores the EXPANDED ed25519 secret key
# (clamped 32-byte scalar || 32-byte SHA-512 prefix); the 32-byte seed
# itself is never written (worker re-seeds per key). The stored scalar
# must satisfy the ed25519 clamping invariant — the exact check
# upstream worker_batch.inc.h applies to every generated key:
#   (sk[0] & 248) == sk[0] and ((sk[31] & 63) | 64) == sk[31]
b0, b31 = sk[0], sk[31]
assert (b0 & 248) == b0, "secret key scalar low byte not clamped"
assert ((b31 & 63) | 64) == b31, "secret key scalar high byte not clamped"

# 4. v3 checksum: SHA3-256(".onion checksum" || PK || 0x03), first 2 bytes
checksum = hashlib.sha3_256(b".onion checksum" + pk + b"\x03").digest()[:2]

# 5. version byte 0x03, then base32 of the 35-byte payload
payload = pk + checksum + b"\x03"
expect = base64.b32encode(payload).decode("ascii").rstrip("=").lower()
assert expect == addr, "address != base32(PK||checksum||0x03)"
sys.exit(0)
EOF
echo "OK: key file format, SHA3-256 checksum and version 0x03 verified"

echo "[test] negative: corrupted key material must fail verification"
# Tamper with the public key file (flip one bit in the PK) and rerun the
# derivation: the address must NOT match any longer. This proves the
# positive check above is a real discriminator, not a tautology.
cp "$PUB" "$PUB.corrupt"
python3 - "$PUB.corrupt" <<'EOF'
import sys
f = sys.argv[1]
data = bytearray(open(f, "rb").read())
data[40] ^= 0x01  # flip a bit inside the 32-byte key part
open(f, "wb").write(bytes(data))
EOF
if python3 - "$PUB.corrupt" "$ADDR_BODY" <<'EOF'
import base64, hashlib, sys
pub = open(sys.argv[1], "rb").read()
addr = sys.argv[2]
pk = pub[-32:]
checksum = hashlib.sha3_256(b".onion checksum" + pk + b"\x03").digest()[:2]
expect = base64.b32encode(pk + checksum + b"\x03").decode().rstrip("=").lower()
sys.exit(0 if expect == addr else 1)
EOF
then
    rm -f "$PUB.corrupt"
    fail "corrupted public key still verified — check is tautological"
fi
rm -f "$PUB.corrupt"
echo "OK: corrupted key correctly rejected (negative check)"

echo "[test] address derived from public key (independent check)"
# python3: base32-decode the address, compare the 32-byte key part with
# the public key file content (torspec proposal 224: onion v3 =
# base32(PK || CHECKSUM(2) || VERSION(1)), 35 bytes -> 56 chars)
python3 - "$PUB" "$ADDR_BODY" <<'EOF' || fail "address does not match public key (base32 decode mismatch)"
import base64, sys
pubfile, addr = sys.argv[1], sys.argv[2]
pub = open(pubfile, "rb").read()
raw = base64.b32decode(addr.upper() + "=" * ((8 - len(addr) % 8) % 8))
sys.exit(0 if raw[:32] == pub[-32:] else 1)
EOF
echo "OK: onion address derives from public key"

echo "[test] cleanup"
rm -rf "$OUTDIR"
[ ! -d "$OUTDIR" ] || fail "cleanup failed"
echo "OK: key material cleaned up"

echo "ALL FUNCTIONAL TESTS PASSED"
