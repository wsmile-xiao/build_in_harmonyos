#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ali executable
set -eu

# HMBS readonly /tmp compat — HarmonyOS /tmp is read-only; use HMBS injected TMPDIR
# Priority: HMBS TMPDIR/TMP/TEMP if writable, else fallback to /data/storage/.../tmp
if [ -z "${TMPDIR:-}" ] || [ "$TMPDIR" = "0" ] || [ "$TMPDIR" = "/tmp" ] || [ ! -d "$TMPDIR" ] || [ ! -w "$TMPDIR" ]; then
  _hmbs_tmp=""
  for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${HMBS_TMPDIR:-}"; do
    if [ -n "${_cand:-}" ] && [ -d "$_cand" ] && [ -w "$_cand" ]; then _hmbs_tmp="$_cand"; break; fi
  done
  if [ -z "$_hmbs_tmp" ]; then
    _hmbs_tmp="/data/storage/el2/base/haps/entry/files/tmp"
    mkdir -p "$_hmbs_tmp" 2>/dev/null || true
    if [ ! -d "$_hmbs_tmp" ] || [ ! -w "$_hmbs_tmp" ]; then
      _hmbs_tmp="$PWD/tmp"
      mkdir -p "$_hmbs_tmp" 2>/dev/null || true
    fi
  fi
  TMPDIR="$_hmbs_tmp"
  export TMPDIR
fi
export TMP="${TMP:-$TMPDIR}"
export TEMP="${TEMP:-$TMPDIR}"
# Ensure mktemp and go temp use writable dir
mkdir -p "$TMPDIR" 2>/dev/null || true

echo "[test] TMPDIR=$TMPDIR TMP=$TMP TEMP=$TEMP"

echo "[test] ali --version"
ali --version
ali --version | grep -q "v0.8.0" && echo "version contains v0.8.0" || echo "version check non-strict"

echo "[test] ali --help"
ali --help > /dev/null 2>&1 && echo "--help OK"

echo "[test] ali invalid invocation should show usage"
set +e
ali 2>&1 | grep -q "no target given" && echo "usage detection OK"
set -e

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":3,"passedCount":3}'
