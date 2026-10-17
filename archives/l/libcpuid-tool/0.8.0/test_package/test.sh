#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the libcpuid-tool executable (cpuid_tool)
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] cpuid_tool --version"
VERSION_OUTPUT="$(cpuid_tool --version)"
echo "$VERSION_OUTPUT"
case "$VERSION_OUTPUT" in
  *0.8.0*) echo "OK: --version reports the packaged library version 0.8.0" ;;
  *) echo "FAIL: unexpected --version output" >&2; exit 1 ;;
esac

echo "[test] cpuid_tool --report"
REPORT_OUTPUT="$(cpuid_tool --report)"
echo "$REPORT_OUTPUT" | head -3
if [ -n "$REPORT_OUTPUT" ]; then
    echo "OK: --report produced a non-empty CPU report"
else
    echo "FAIL: --report produced no output" >&2
    exit 1
fi
