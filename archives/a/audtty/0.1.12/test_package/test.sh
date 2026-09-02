#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for audtty executable
# HMBS: use TMPDIR chain for readonly /tmp, ensure TERM, show output for diagnosis
set -eu

# HMBS readonly /tmp handling
TMPDIR="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="${TMP:-$TMPDIR}"
export TEMP="${TEMP:-$TMPDIR}"
export TERM="${TERM:-xterm}"
echo "[test] TMPDIR=$TMPDIR TERM=$TERM"
echo "[test] which audtty: $(which audtty 2>&1 || echo not-found)"
echo "[test] PATH=$PATH"
echo "[test] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-unset}"

help_out="$TMPDIR/audtty_help_$$.txt"
ver_out="$TMPDIR/audtty_version_$$.txt"

echo "[test] audtty --help (capture to $help_out)"
if [ -x "$(which audtty 2>/dev/null || echo /nonexistent)" ]; then
  audtty --help > "$help_out" 2>&1 || true
else
  audtty --help > "$help_out" 2>&1 || true
fi
echo "--- audtty --help output (cat $help_out) ---"
cat "$help_out" 2>&1 || echo "(empty or missing)"
echo "--- end help output ---"
# Check non-empty and contains Usage
if [ -s "$help_out" ] && grep -qi "Usage" "$help_out"; then
  echo "[PASS] audtty --help (non-empty, contains Usage)"
  help_ok=1
else
  echo "[FAIL] audtty --help (missing Usage or empty)"
  # Also try alternative check for help string
  if grep -qi "audtty" "$help_out" 2>/dev/null; then
    echo "[INFO] help output contains audtty but not Usage"
  fi
  help_ok=0
fi

echo "[test] audtty --version (capture to $ver_out)"
audtty --version > "$ver_out" 2>&1 || true
echo "--- audtty --version output (cat $ver_out) ---"
cat "$ver_out" 2>&1 || echo "(empty or missing)"
echo "--- end version output ---"
if [ -s "$ver_out" ] && grep -qi "version" "$ver_out"; then
  echo "[PASS] audtty --version (non-empty, contains version)"
  ver_ok=1
else
  echo "[FAIL] audtty --version (missing version or empty)"
  ver_ok=0
fi

# Count
discovered=2
passedCount=$((help_ok + ver_ok))
echo "[test] discovered=$discovered passed=$passedCount"

# HMBS marker (also emitted from conanfile.py, duplicated for robustness)
if [ "$passedCount" -eq "$discovered" ]; then
  echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"audtty --help; audtty --version","discovered":2,"passedCount":2}'
else
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"audtty --help; audtty --version\",\"discovered\":2,\"passedCount\":$passedCount}"
  exit 1
fi
