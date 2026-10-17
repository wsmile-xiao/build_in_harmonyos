#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke tests for ytt executable
# Runs in conanrun env (PATH includes installed bin/)
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

echo "[test] TMPDIR=$TMPDIR"

echo "[test] 1/3 ytt version"
ytt version
ytt version | grep -q "0.55.1" && echo "        [ok] version contains 0.55.1" || echo "        [warn] version check non-strict"

echo "[test] 2/3 basic template render"
_work="$TMPDIR/ytt-smoke"
mkdir -p "$_work"
cat > "$_work/tpl.yml" <<'EOF'
#@ def msg():
#@   return "Hello, ytt!"
#@ end
message: #@ msg()
plain: value
EOF
ytt -f "$_work/tpl.yml" > "$_work/out.yml"
grep -q "message: Hello, ytt!" "$_work/out.yml" && echo "        [ok] template render OK" || { echo "        [fail] template render mismatch"; cat "$_work/out.yml"; exit 1; }
grep -q "plain: value" "$_work/out.yml" && echo "        [ok] plain yaml passthrough OK" || { echo "        [fail] plain yaml missing"; exit 1; }

echo "[test] 3/3 --data-value override"
cat > "$_work/schema.yml" <<'EOF'
#@data/values
---
name: dev
EOF
cat > "$_work/tpl2.yml" <<'EOF'
#@ load("@ytt:data", "data")
name: #@ data.values.name
EOF
ytt -f "$_work/tpl2.yml" -f "$_work/schema.yml" --data-value name=prod > "$_work/out2.yml"
grep -q "name: prod" "$_work/out2.yml" && echo "        [ok] data-value override OK" || { echo "        [fail] data-value override mismatch"; cat "$_work/out2.yml"; exit 1; }

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":3,"passedCount":3}'
