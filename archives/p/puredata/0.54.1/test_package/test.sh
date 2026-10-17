#!/usr/bin/env bash
# test_package/test.sh — smoke test for the puredata executable.
# Runs in conanrun env (PATH includes the installed bin/).
# NOTE: loopback TCP (pdsend/pdreceive roundtrip) and audio devices are
# unavailable in the sandboxed CI runner, so the functional test drives
# pd headless over stdin FUDI ("; pd quit;") instead.
set -euo pipefail

echo "[test] pd -version"
version_output=$(timeout 30 pd -version 2>&1)
echo "$version_output"
echo "$version_output" | grep -q "Pd-0.54" || {
    echo "FAIL: pd -version did not report Pd-0.54"
    exit 1
}
echo "PASS: pd -version reports Pd-0.54"

echo "[test] headless pd boots and processes a FUDI quit message"
# -send "; pd quit;": pd must start its scheduler, parse the FUDI message
# and exit cleanly (rc=0). This exercises the interpreter, the scheduler
# and the message parser — a real functional roundtrip.
set +e
timeout 60 pd -nogui -nosound -send "; pd quit;" >/dev/null 2>&1
headless_rc=$?
set -e
[ "$headless_rc" -eq 0 ] || {
    echo "FAIL: headless pd did not exit cleanly on FUDI quit (rc=$headless_rc)"
    exit 1
}
echo "PASS: headless pd FUDI quit roundtrip"

echo "[test] pdsend/pdreceive installed"
command -v pdsend >/dev/null || { echo "FAIL: pdsend missing"; exit 1; }
command -v pdreceive >/dev/null || { echo "FAIL: pdreceive missing"; exit 1; }
echo "PASS: pdsend/pdreceive installed"

echo "[test] puredata data dir (lib/pd) installed"
# R34 / CI L1e: pd 运行时依赖包内数据目录 lib/pd（externals/startup/tcl/doc）。
# L1e 破坏性负向测试会移走包内 lib/；此检查在数据目录缺失时失败，
# 证明 test 真实依赖被测包产物（与 pd -version 等 bin 依赖互补，
# 并规避包内嵌套 bin/（lib/pd/bin）导致 L1e find 破坏错位的问题）。
pd_bin_dir="$(cd "$(dirname "$(command -v pd)")" && pwd)"
pkg_root="$(cd "$pd_bin_dir/.." && pwd)"
[ -d "$pkg_root/lib/pd" ] || {
    echo "FAIL: puredata data dir lib/pd missing (package data not installed)"
    exit 1
}
echo "PASS: puredata data dir installed at $pkg_root/lib/pd"

echo "[test] all PASS"
