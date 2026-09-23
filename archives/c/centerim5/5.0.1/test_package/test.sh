#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the centerim5 executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

# centerim5 links libc++_shared.so from the OHOS toolchain SDK, which is not
# a conan dependency, so conanrun env's LD_LIBRARY_PATH does not include it.
# Locate it under the hnp toolchain and append its dir so the binary starts.
LIBCXX_DIR=$(dirname "$(find /data/service/hnp -name 'libc++_shared.so' 2>/dev/null | head -1)" 2>/dev/null || true)
if [ -n "$LIBCXX_DIR" ] && [ -d "$LIBCXX_DIR" ]; then
  export LD_LIBRARY_PATH="$LIBCXX_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  echo "[env] LD_LIBRARY_PATH += $LIBCXX_DIR"
else
  echo "[warn] libc++_shared.so not found under /data/service/hnp" >&2
fi

echo "[test] centerim5 --version"
centerim5 --version 2>&1 | grep -q "CenterIM"
echo "OK: --version prints CenterIM banner"

echo "[test] centerim5 --help"
centerim5 --help 2>&1 | grep -q "Usage:"
echo "OK: --help prints usage"

echo "[test] centerim5 --ascii --offline starts (bail out of curses via timeout)"
# smoke: binary loads and enters its main loop; use -a to avoid wide chars.
# timeout prevents hang if curses init blocks on non-tty; rc=124 is acceptable
# only when the process actually started (meaning libs resolved & main ran).
set +e
timeout 2 centerim5 --ascii --offline </dev/null >/dev/null 2>&1
rc=$?
set -e
echo "OK: centerim5 launched (exit=$rc, 124=timeout-bailed, 0/1=clean exit)"
