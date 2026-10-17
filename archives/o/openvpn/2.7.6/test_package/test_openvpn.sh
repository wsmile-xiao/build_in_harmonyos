#!/usr/bin/env bash
# test_openvpn.sh — functional verification for the packaged openvpn binary.
# Runs end-to-end against the installed openvpn CLI (R34):
#   1. --version: version string, OHOS platform triplet, feature marks
#   2. --show-ciphers / --show-digests / --show-tls: embedded OpenSSL listings
#   3. --genkey secret: static key generation
#   4. static-key dev-null tunnel: TLS-less data path smoke (deprecated path
#      explicitly allowed via --allow-deprecated-insecure-static-crypto;
#      ping-exit 4 exits cleanly after 4s of inactivity)
# Usage: test_openvpn.sh <path-to-openvpn-binary> [workdir]
set -euo pipefail

BIN=${1:?usage: test_openvpn.sh <openvpn-binary> [workdir]}
WORKDIR=${2:-$(mktemp -d)}
trap 'rm -rf "$WORKDIR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "ok   : $*"; }

# --- 1/4 version / platform / feature marks -------------------------------
VER=$("$BIN" --version 2>&1 | head -1)
echo "$VER"
case "$VER" in
    "OpenVPN 2.7.6 "*) : ;;
    *) fail "unexpected --version output: $VER" ;;
esac
for feat in aarch64-unknown-linux-ohos "[SSL (OpenSSL)]" "[LZO]" "[LZ4]" "[EPOLL]" "[AEAD]"; do
    case "$VER" in *"$feat"*) : ;; *) fail "feature mark missing: $feat" ;; esac
done
ok "version/platform/feature marks"

# --- 2/4 crypto capability listings (embedded OpenSSL) --------------------
for arg in --show-ciphers --show-digests --show-tls; do
    N=$("$BIN" "$arg" 2>/dev/null | wc -l)
    [ "$N" -ge 10 ] || fail "$arg produced only $N lines"
    ok "$arg ($N entries)"
done

# --- 3/4 static key generation --------------------------------------------
KEYFILE="$WORKDIR/static.key"
"$BIN" --genkey secret "$KEYFILE"
[ -s "$KEYFILE" ] || fail "--genkey secret produced empty key file"
ok "--genkey secret (static key generated)"

# --- 4/4 static-key dev-null tunnel ----------------------------------------
CFG="$WORKDIR/t.conf"
cat > "$CFG" <<EOF
dev null
ifconfig 10.9.8.1 10.9.8.2
allow-deprecated-insecure-static-crypto
cipher AES-256-CBC
auth SHA256
secret $KEYFILE
ping 1
ping-exit 4
verb 3
EOF
# ping-exit 4: exit cleanly (exit 0) after ~4s of no traffic — reaching that
# point proves the TLS-less static-key data path (cipher init, buffer, null
# tun device) ran cleanly. (ping-restart would soft-restart forever.)
OUT=$("$BIN" --config "$CFG" --suppress-timestamps 2>&1) || { echo "$OUT"; fail "tunnel exited non-zero"; }
echo "$OUT" | head -8
echo "$OUT" | grep -q "device .* opened" || fail " device was not opened"
ok "static-key dev-null tunnel ran"

echo "ALL OPENVPN TESTS PASSED"
