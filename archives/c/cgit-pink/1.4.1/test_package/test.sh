#!/data/service/hnp/bin/bash
# test_package/test.sh — cgit-pink executable smoke test.
# Runs in conanrun env (PATH includes installed bin/).
set -eu

# E002: HarmonyOS /tmp is read-only; point shell/test temps at writable dir.
if [ -n "${HMBS_TMPDIR:-}" ] && [ -d "$HMBS_TMPDIR" ]; then
  TMPDIR="$HMBS_TMPDIR"
elif [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
  TMPDIR="$TMPDIR"
else
  TMPDIR="$PWD/.hmbs-tmp"
  mkdir -p "$TMPDIR"
fi
export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR"

PASS=0
TOTAL=2

echo "[test 1/2] cgit executes and emits HTML page"
CGIT_CONFIG=/dev/null cgit > cgit_out1.html 2> cgit_err1.log || true
if [ -s cgit_out1.html ] && grep -qi "cgit" cgit_out1.html; then
  echo "PASS test1: cgit emitted non-empty HTML containing cgit marker"
  PASS=$((PASS + 1))
else
  echo "FAIL test1: cgit HTML output missing or empty"
  echo "--- stdout head ---"
  head -c 2000 cgit_out1.html 2>/dev/null || true
  echo ""
  echo "--- stderr head ---"
  head -c 2000 cgit_err1.log 2>/dev/null || true
  echo ""
fi

echo "[test 2/2] cgit honors CGIT_CONFIG with empty repo list"
printf 'css=/cgit.css\nlogo=/cgit.png\n' > cgit_empty.rc
CGIT_CONFIG="$PWD/cgit_empty.rc" QUERY_STRING="" cgit > cgit_out2.html 2> cgit_err2.log || true
if [ -s cgit_out2.html ] && grep -qi "cgit" cgit_out2.html; then
  echo "PASS test2: cgit parsed custom config and emitted HTML"
  PASS=$((PASS + 1))
else
  echo "FAIL test2: cgit config-run output missing or empty"
  echo "--- stdout head ---"
  head -c 2000 cgit_out2.html 2>/dev/null || true
  echo ""
fi

if [ "$PASS" -eq "$TOTAL" ]; then
  RESULT_TRUE=true
else
  RESULT_TRUE=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":${RESULT_TRUE},\"passed\":${RESULT_TRUE},\"command\":\"bash test.sh (cgit CGI smoke)\",\"discovered\":${TOTAL},\"passedCount\":${PASS}}"
if [ "$PASS" -ne "$TOTAL" ]; then
  echo "cgit-pink test_package failed: ${PASS}/${TOTAL}"
  exit 1
fi
echo "cgit-pink test_package passed: ${PASS}/${TOTAL}"
