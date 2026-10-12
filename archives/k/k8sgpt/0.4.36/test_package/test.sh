#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for k8sgpt executable
set -eu

# HMBS readonly /tmp compat — HarmonyOS /tmp is read-only; use HMBS injected TMPDIR
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
mkdir -p "$TMPDIR" 2>/dev/null || true

echo "[test] TMPDIR=$TMPDIR TMP=$TMP TEMP=$TEMP"

echo "[test] k8sgpt version"
k8sgpt version
k8sgpt version | grep -q "v0.4.36" && echo "version contains v0.4.36" || { echo "version check FAILED"; exit 1; }

echo "[test] k8sgpt --help"
k8sgpt --help > /dev/null 2>&1 || { echo "--help check FAILED"; exit 1; }
echo "--help OK"

echo "[test] k8sgpt no-args usage"
k8sgpt 2>&1 | grep -q "Usage:" || { echo "usage check FAILED"; exit 1; }
echo "usage detection OK"

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":3,"passedCount":3}'
