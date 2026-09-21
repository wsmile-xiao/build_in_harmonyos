#!/bin/sh
# test_package/test_xdelta.sh — xdelta 1.1.3 consumer functional test.
# Runs in the conanrun environment (bin/ from the built package on PATH).
# Each case asserts on real artifacts (non-empty files, byte-identical
# reconstruction, version output), so an exit-1 stub binary cannot fake a pass:
#   TC1: xdelta --version reports 1.1.3
#   TC2: xdelta delta produces a non-empty delta (exit 0/1 per man page:
#        0=no differences, 1=differences found, 2=error)
#   TC3: xdelta patch reconstructs the target byte-identical (MD5 verified
#        by xdelta itself unless --noverify is given)
#   TC4: xdelta info describes the delta
set -u

discovered=4
passed=0
failed=0

work="${TMPDIR:-/tmp}/xdelta-test-$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

# TC1: version output is non-empty and mentions 1.1.3
# xdelta 1.1.3 uses getopt-style exit codes: `xdelta --version` prints
# "xdelta: version 1.1.3" but exits 2 (preflight: rc=2 with correct
# output). Require the version string, not rc==0; an exit-1 stub with
# empty/wrong output still fails here.
ver_out="$(xdelta --version 2>&1)"
ver_rc=$?
if [ -n "$ver_out" ]; then
  case "$ver_out" in
    *1.1.3*)
      passed=$((passed + 1))
      echo "[ok] TC1: xdelta --version reports 1.1.3 (rc=$ver_rc, $ver_out)"
      ;;
    *)
      failed=$((failed + 1))
      echo "[fail] TC1: version output does not mention 1.1.3: $ver_out"
      ;;
  esac
else
  failed=$((failed + 1))
  echo "[fail] TC1: xdelta --version failed (rc=$ver_rc, out=$ver_out)"
fi

# Fixtures must be non-empty; otherwise delta/patch comparisons are vacuous.
printf 'The quick brown fox jumps over the lazy dog. Source revision one.\n' > "$work/old.bin"
printf 'The quick brown fox jumps over the lazy cat. Target revision two with more content.\n' > "$work/new.bin"
if [ ! -s "$work/old.bin" ] || [ ! -s "$work/new.bin" ]; then
  echo "[fail] fixtures are empty, aborting (refusing vacuous pass)"
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test_xdelta.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
  exit 1
fi

# TC2: delta (accept rc 0 or 1; rc 2 is a real error)
set +u
xdelta delta "$work/old.bin" "$work/new.bin" "$work/patch.xd" >/dev/null 2>&1
delta_rc=$?
set -u
if { [ $delta_rc -eq 0 ] || [ $delta_rc -eq 1 ]; } && [ -s "$work/patch.xd" ]; then
  passed=$((passed + 1))
  echo "[ok] TC2: xdelta delta produced non-empty patch (rc=$delta_rc, $(wc -c < "$work/patch.xd") bytes)"
else
  failed=$((failed + 1))
  echo "[fail] TC2: xdelta delta failed (rc=$delta_rc)"
fi

# TC3: patch reconstructs new.bin byte-identical
xdelta patch "$work/patch.xd" "$work/old.bin" "$work/rebuilt.bin" >/dev/null 2>&1
patch_rc=$?
if [ $patch_rc -eq 0 ] && [ -s "$work/rebuilt.bin" ] && cmp -s "$work/rebuilt.bin" "$work/new.bin"; then
  passed=$((passed + 1))
  echo "[ok] TC3: xdelta patch reconstructed target byte-identical"
else
  failed=$((failed + 1))
  echo "[fail] TC3: reconstruction mismatch or patch failed (rc=$patch_rc)"
fi

# TC4: info output is non-empty
info_out="$(xdelta info "$work/patch.xd" 2>&1)"
info_rc=$?
if [ $info_rc -eq 0 ] && [ -n "$info_out" ]; then
  passed=$((passed + 1))
  echo "[ok] TC4: xdelta info described the delta"
  echo "$info_out" | head -5 | sed 's/^/      /'
else
  failed=$((failed + 1))
  echo "[fail] TC4: xdelta info failed (rc=$info_rc)"
fi

if [ $failed -eq 0 ]; then
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test_xdelta.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
  exit 0
else
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test_xdelta.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
  exit 1
fi
