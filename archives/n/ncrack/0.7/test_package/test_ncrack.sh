#!/bin/sh
# ncrack 0.7 consumer test — real execution of the installed binary.
#
#   1) `ncrack --version`      : identity + OpenSSL-enabled module table
#   2) closed-port local scan  : scan engine / nsock / output layer really run
#
# Usage: test_ncrack.sh <path-to-ncrack> <path-to-share/ncrack>
# Exits non-zero with a diagnostic line on any assertion failure.
#
# NCRACKDIR is exported because ncrack resolves its data files (ncrack-services,
# lists/*) *before* option parsing: the search order is --datadir (not seen yet)
# -> $NCRACKDIR -> ~user/.ncrack -> the compiled-in NCRACKDATADIR (an absolute
# "/share/ncrack" under the recipe's --prefix=/, which cannot point at a conan
# package folder) -> cwd.  Without NCRACKDIR the binary exits 1 with
# "lookup_init: failed to open file ncrack-services for reading!".

set -u

BIN="$1"
DATADIR="$2"

fail() {
    echo "test_ncrack.sh: FAIL: $1"
    exit 1
}

[ -x "$BIN" ] || fail "binary not executable: $BIN"
[ -d "$DATADIR" ] || fail "data dir missing: $DATADIR"
[ -f "$DATADIR/ncrack-services" ] || fail "ncrack-services missing in $DATADIR"

NCRACKDIR="$DATADIR"
export NCRACKDIR

echo "--- ncrack --version ---"
OUT=$("$BIN" --version 2>&1)
RC=$?
echo "$OUT"
[ "$RC" -eq 0 ] || fail "--version exited with $RC"
echo "$OUT" | grep -q "Ncrack version 0.7" || fail "version string missing"
echo "$OUT" | grep -q "Modules:" || fail "module table missing"
# The RDP module is compiled through the OpenSSL code path (ntlmssp.cc);
# its presence in the module line proves the OpenSSL link really happened.
echo "$OUT" | grep -q "RDP" || fail "RDP module absent (OpenSSL link missing?)"

echo "--- local scan of a closed port (127.0.0.1:9, rdp module) ---"
# -p takes a SERVICE name (a bare port is rejected: "Service with default port
# '9' not supported! Ignoring..."); a non-default port is given as
# <service>:<port>.  rdp is chosen because that module compiles through the
# OpenSSL-backed code (ntlmssp.cc).  A closed port yields a clean, deterministic
# run: one service scanned, no credentials.
OUT=$("$BIN" -p rdp:9 -T 4 --datadir "$DATADIR" 127.0.0.1 2>&1)
RC=$?
echo "$OUT"
[ "$RC" -eq 0 ] || fail "scan exited with $RC"
echo "$OUT" | grep -q "Ncrack done: 1 service scanned" || fail "unexpected scan summary"
echo "$OUT" | grep -q "Ncrack finished." || fail "scan did not finish cleanly"
if echo "$OUT" | grep -q "Discovered credentials"; then
    fail "credentials reported for a closed port"
fi

echo "test_ncrack.sh: PASS"
