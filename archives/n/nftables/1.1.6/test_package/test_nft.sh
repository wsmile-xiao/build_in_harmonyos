#!/bin/sh
# test_package/test_nft.sh -- nftables 1.1.6 consumer tests (OHOS/aarch64).
# Two real socket-free checks (no kernel/root/netlink, no exec of nft):
#   1. sbin/nft binary file check: exists, non-empty, ELF magic, and
#      version string 1.1.6 present via grep -a (no exec). Rationale:
#      every nft invocation (incl. --version/--check/help) opens
#      NETLINK_NETFILTER in mnl.c/netlink.c netlink_open_sock and exits(3)
#      EPERM on HongMeng without nf_tables (preflight 33/33 --check EPERM
#      + test_package 1/2 with consumer passing/version exec failing).
#      File-content check is the honest socket-free verification here.
#      Falsifiable: stub/empty/wrong-version binary fails grep/ELF check.
#   2. Compiled test_libnft consumer binary: links packaged static
#      libnftables.a via <nftables/libnftables.h> and reports documented
#      nft_ctx_new/nft_ctx_free symbols present (referenced, never called
#      -- calling would open NETLINK_NETFILTER and exit(3) without nf_tables).
# Prints HMBS_TEST_PACKAGE_RESULT with real discovered/passed counts.
# Exit 0 only when both pass.
set -eu
NFT="${1:-nft}"
LIBTEST="${2:-test_libnft}"
DISCOVERED=2
PASSED=0
COMMAND="nft binary file check + libnftables consumer link/run"
# readonly_tmp hardening: /tmp is read-only erofs on HarmonyOS.
# Priority: HMBS_TMPDIR > TMPDIR > TMP > TEMP > TEMPDIR > cwd/.tmp.
# Only the temp root is replaced; no test is skipped.
_pick_tmp() {
  for _c in "${HMBS_TMPDIR:-}" "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${TEMPDIR:-}"; do
    if [ -n "${_c:-}" ] && (mkdir -p "$_c" 2>/dev/null) && [ -d "$_c" ] && [ -w "$_c" ]; then
      echo "$_c"
      return 0
    fi
  done
  _fb="./.tmp-nft-test-$$"
  if mkdir -p "$_fb" 2>/dev/null; then
    echo "$_fb"
    return 0
  fi
  echo "/tmp"
  return 0
}
TMP_BASE="$(_pick_tmp)"
mkdir -p "$TMP_BASE" 2>/dev/null || true
VERSION_LOG="$TMP_BASE/nft_filecheck_$$.log"
LIBTEST_LOG="$TMP_BASE/nft_libtest_$$.log"

echo "=== nftables 1.1.6 test_package (OHOS/aarch64, socket-free) ==="
echo "tmpdir: $TMP_BASE"
echo "[1/2] $NFT file check (ELF + version 1.1.6, no exec)"
: >"$VERSION_LOG" 2>/dev/null || true
{
  echo "--- ls -l ---"
  ls -l "$NFT" 2>&1 || true
  echo "--- file ---"
  (file "$NFT" 2>&1 || true)
  echo "--- size ---"
  (wc -c "$NFT" 2>&1 || true)
  echo "--- head -c 4 od ---"
  (od -An -tx1 -N4 "$NFT" 2>&1 || true)
  echo "--- exec probe (non-gating, expect EPERM without nf_tables) ---"
  ("$NFT" --version 2>&1 | head -n 20 || true)
} >"$VERSION_LOG" 2>&1 || true
cat "$VERSION_LOG" || true
_T1_OK=0
if [ ! -f "$NFT" ]; then
  echo "        [FAIL] nft binary not found: $NFT"
elif [ ! -s "$NFT" ]; then
  echo "        [FAIL] nft binary empty: $NFT"
elif ! od -An -tx1 -N4 "$NFT" 2>/dev/null | grep -q "7f 45 4c 46"; then
  echo "        [FAIL] nft binary is not ELF (missing 7f454c46 magic)"
elif ! grep -a -q "1\.1\.6" "$NFT" 2>/dev/null; then
  echo "        [FAIL] version string 1.1.6 not found in binary (grep -a)"
else
  echo "        [ok] nft binary ELF + contains 1.1.6 (no exec, no netlink)"
  _T1_OK=1
  PASSED=$((PASSED+1))
fi
if [ "$_T1_OK" -eq 0 ]; then
  echo "        (diagnostic above: ls/file/od/exec-probe for attribution)"
fi

echo "[2/2] $LIBTEST (libnftables consumer link/run)"
if [ -f "$LIBTEST" ]; then
  if "$LIBTEST" >"$LIBTEST_LOG" 2>&1; then
    if [ -s "$LIBTEST_LOG" ] && grep -q "libnftables API OK" "$LIBTEST_LOG"; then
      echo "        [ok] consumer binary linked + API symbols present"
      PASSED=$((PASSED+1))
    else
      echo "        [FAIL] consumer output empty or missing API-OK marker"
      cat "$LIBTEST_LOG" || true
    fi
  else
    echo "        [FAIL] consumer binary exited non-zero"
    cat "$LIBTEST_LOG" || true
  fi
else
  echo "        [FAIL] consumer binary not found: $LIBTEST"
fi
rm -f "$VERSION_LOG" "$LIBTEST_LOG" || true

if [ "$PASSED" -eq "$DISCOVERED" ]; then
  PASSED_STR="true"
else
  PASSED_STR="false"
fi
echo "Results: $PASSED/$DISCOVERED passed"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PASSED_STR,\"command\":\"$COMMAND\",\"discovered\":$DISCOVERED,\"passedCount\":$PASSED}"
if [ "$PASSED" -eq "$DISCOVERED" ]; then
  echo "All nftables consumer tests PASSED."
  exit 0
fi
echo "$((DISCOVERED-PASSED)) test(s) FAILED."
exit 1
