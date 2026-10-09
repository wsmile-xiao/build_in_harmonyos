#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the k2tf executable
set -u

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
mkdir -p "$TMPDIR" 2>/dev/null || true

echo "[test] TMPDIR=$TMPDIR TMP=$TMP TEMP=$TEMP"

_fail=0

# ---- Case 1: version output ----
echo "[test] k2tf -v (version)"
if k2tf -v | grep -q "v0.8.0"; then
  echo "[test] OK: version contains v0.8.0"
else
  echo "[test] FAIL: '-v' did not print version"
  _fail=1
fi

# ---- Case 2: help output (k2tf exits with code 2 on --help by design; assert output only) ----
echo "[test] k2tf --help"
if k2tf --help 2>&1 | grep -q "Usage of"; then
  echo "[test] OK: help text present"
else
  echo "[test] FAIL: '--help' did not print usage"
  _fail=1
fi

# ---- Case 3: end-to-end stdin YAML -> HCL conversion ----
echo "[test] k2tf stdin Service YAML -> HCL conversion"
if printf 'apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\nspec:\n  selector:\n    app: foo\n  ports:\n    - port: 80\n' | k2tf | grep -q 'resource "kubernetes_service" "my_svc"'; then
  echo "[test] OK: converted to kubernetes_service resource"
else
  echo "[test] FAIL: stdin conversion did not produce kubernetes_service resource"
  _fail=1
fi

if [ "$_fail" -ne 0 ]; then
  echo "[test] smoke test FAILED"
  exit 1
fi

echo "[test] all smoke tests passed"
echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":3,"passedCount":3}'
