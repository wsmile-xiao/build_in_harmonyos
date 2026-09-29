#!/bin/sh
# run_ohos_test.sh — independent build/run entry for the HarmonyOS-specific
# libnss-cache 0.22 test (ohos_nss_cache_test.c).
#
# This entry is separate from test_package/: it compiles the test source with
# the OHOS clang toolchain against the built libnss-cache package and runs it
# three times:
#   1) positive   — assertions hold, exit 0
#   2) negative   — OHOS_NSS_CACHE_INJECT_FAIL=1 flips an expected value to an
#                   impossible one -> real non-zero exit + FAIL text
#   3) restore    — plain run passes again
#
# Usage: run_ohos_test.sh [pkg_dir] [log_dir]
#   pkg_dir  : directory containing include/ and lib/libnss_cache.so.2
#              (default: auto-locate the conan cache package)
#   log_dir  : writable output dir (default $TMPDIR, fallback $HOME/tmp)
#
# All outputs go to log_dir (never /tmp).

set -u

PKG_DIR="${1:-}"
LOG_DIR="${2:-${TMPDIR:-$HOME/tmp}}"

if [ -z "$PKG_DIR" ]; then
  # Auto-locate the built OHOS package in the conan cache.
  PKG_DIR="$(find "$HOME/.conan2" -name 'libnss_cache.so.2' -path '*/p/*' 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname 2>/dev/null || true)"
fi
if [ -z "$PKG_DIR" ] || [ ! -f "$PKG_DIR/lib/libnss_cache.so.2" ]; then
  echo "ERROR: libnss-cache package not found; pass pkg_dir as arg 1" >&2
  exit 4
fi

mkdir -p "$LOG_DIR" || { echo "ERROR: cannot create log dir $LOG_DIR" >&2; exit 4; }

TEST_SRC="$(dirname "$0")/ohos_nss_cache_test.c"
CC="${OHOS_TEST_CC:-/data/service/hnp/bin/clang}"
OUT="$LOG_DIR/ohos_nss_cache_test.bin"
LOG="$LOG_DIR/ohos_nss_cache_test_run.log"

: > "$LOG"
echo "=== libnss-cache 0.22 HarmonyOS-specific test (independent entry) ===" | tee -a "$LOG"
echo "pkg_dir=$PKG_DIR" | tee -a "$LOG"
echo "log_dir=$LOG_DIR" | tee -a "$LOG"
date -u +'UTC %Y-%m-%dT%H:%M:%SZ' | tee -a "$LOG"

# 1) compile
echo "--- compile ---" | tee -a "$LOG"
"$CC" -I"$PKG_DIR/include" "$TEST_SRC" -L"$PKG_DIR/lib" -lnss_cache -o "$OUT" 2>&1 | tee -a "$LOG"
COMPILE_RC=${PIPESTATUS:-0}
[ -z "${PIPESTATUS:-}" ] && COMPILE_RC=$?
echo "compile rc=$COMPILE_RC" | tee -a "$LOG"
if [ "$COMPILE_RC" -ne 0 ] || [ ! -x "$OUT" ]; then
  echo "RESULT: COMPILE_FAILED" | tee -a "$LOG"
  exit 5
fi

run_one() {
  name="$1"; shift
  echo "--- run: $name ---" | tee -a "$LOG"
  ( cd "$LOG_DIR" && env LD_LIBRARY_PATH="$PKG_DIR/lib" "$@" "$OUT" ) 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS:-0}
  [ -z "${PIPESTATUS:-}" ] && rc=$?
  echo "run($name) rc=$rc" | tee -a "$LOG"
  return "$rc"
}

POS_RC=0; NEG_RC=0; RES_RC=0
run_one positive 2>/dev/null; POS_RC=$?
run_one negative env OHOS_NSS_CACHE_INJECT_FAIL=1; NEG_RC=$?
run_one restore 2>/dev/null; RES_RC=$?

echo "=== summary ===" | tee -a "$LOG"
echo "positive rc=$POS_RC (expect 0)" | tee -a "$LOG"
echo "negative rc=$NEG_RC (expect non-zero)" | tee -a "$LOG"
echo "restore  rc=$RES_RC (expect 0)" | tee -a "$LOG"
if [ "$POS_RC" -eq 0 ] && [ "$NEG_RC" -ne 0 ] && [ "$RES_RC" -eq 0 ]; then
  echo "RESULT: HARMONYOS_TEST_PASS" | tee -a "$LOG"
  exit 0
else
  echo "RESULT: HARMONYOS_TEST_FAIL" | tee -a "$LOG"
  exit 1
fi
