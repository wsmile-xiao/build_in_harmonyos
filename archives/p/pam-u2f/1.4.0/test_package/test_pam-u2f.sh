#!/bin/sh
# test_pam-u2f.sh — consumer smoke test for pam-u2f 1.4.0 (R34 real test).
# Case 1: pamu2fcfg --version executes and prints a version string.
# Case 2: pam_u2f.so exists and exports pam_sm_authenticate.
set -eu

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "== case 1: pamu2fcfg --version =="
pamu2fcfg --version || fail "pamu2fcfg --version failed"
echo "PASS: pamu2fcfg runs"

echo "== case 2: pam_u2f.so symbol check =="
MODULE_CANDIDATES="${PAM_U2F_MODULE_DIR:-}/pam_u2f.so"
NM="${NM:-nm}"
FOUND=""
for cand in $MODULE_CANDIDATES; do
  if [ -f "$cand" ]; then FOUND="$cand"; break; fi
done
if [ -z "$FOUND" ]; then
  # Fall back to PATH-relative lookup: ../lib/security/pam_u2f.so
  BIN="$(command -v pamu2fcfg || true)"
  if [ -n "$BIN" ]; then
    CAND="$(dirname "$(dirname "$BIN")")/lib/security/pam_u2f.so"
    if [ -f "$CAND" ]; then FOUND="$CAND"; fi
  fi
fi
[ -n "$FOUND" ] || fail "pam_u2f.so not found"
echo "module: $FOUND"
if command -v "$NM" >/dev/null 2>&1; then
  "$NM" -D "$FOUND" | grep -q pam_sm_authenticate || fail "pam_sm_authenticate missing"
elif command -v llvm-nm >/dev/null 2>&1; then
  llvm-nm -D "$FOUND" | grep -q pam_sm_authenticate || fail "pam_sm_authenticate missing"
else
  fail "no nm tool available"
fi
echo "PASS: pam_u2f.so exports pam_sm_authenticate"

echo "ALL 2 CONSUMER CASES PASSED"
