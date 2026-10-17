#!/data/service/hnp/bin/bash
# test_air_quality_sensor.sh — consumer smoke test for the air-quality-sensor
# CLI (R34: genuinely executes the tested package's binary).
# Runs in conanrun env (PATH includes the installed bin/, LD_LIBRARY_PATH
# includes libusb-1.0). Upstream 0.1.5 ships no test suite (audited), so the
# test_package cases are the on-device verification, and the upstream marker
# reports no_tests with the audit reason.
set -u

BIN="air-quality-sensor"
discovered=3
passed=0
failed=0

echo "[test] $BIN --version"
VOUT=$("$BIN" --version 2>&1)
VRC=$?
echo "$VOUT"
if [ "$VRC" -eq 0 ] && echo "$VOUT" | grep -q "0.1.5"; then
    passed=$((passed + 1))
    echo "[OK] --version prints a 0.1.5 version line"
else
    failed=$((failed + 1))
    echo "[FAIL] --version rc=$VRC, expected 0.1.5 in output"
fi

echo "[test] $BIN --help"
HOUT=$("$BIN" --help 2>&1)
HRC=$?
echo "$HOUT"
if [ "$HRC" -eq 0 ] && echo "$HOUT" | grep -q "Usage:"; then
    passed=$((passed + 1))
    echo "[OK] --help prints usage"
else
    failed=$((failed + 1))
    echo "[FAIL] --help rc=$HRC, expected Usage: line"
fi

echo "[test] $BIN (bare run, no sensor attached)"
BOUT=$("$BIN" 2>&1)
BRC=$?
echo "$BOUT"
# 上游 main() 语义 (src/air10.c): exit(ret ? EXIT_FAILURE : EXIT_SUCCESS)，
# ret 是 find_devices 累加的 libusb 错误。无匹配传感器时：
#   - USB 总线完全可读            -> rc=0（干净退出）
#   - 受限环境读不到 USB 描述符    -> rc=1（libusb 错误，属上游正常语义）
# 两者都是二进制的正常退出路径；崩溃/信号退出（rc>128 等）才是真实失败。
case "$BRC" in
    0)
        passed=$((passed + 1))
        echo "[OK] bare run exits 0 (no matching sensor, clean exit)"
        ;;
    1)
        passed=$((passed + 1))
        echo "[OK] bare run exits 1 (libusb/USB error: no readable sensor in this environment)"
        ;;
    *)
        failed=$((failed + 1))
        echo "[FAIL] bare run rc=$BRC (unexpected exit / crash)"
        ;;
esac

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_air_quality_sensor.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_air_quality_sensor.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"air-quality-sensor 0.1.5 上游无测试套件：源码树无 tests/ 目录，Makefile.am 无 check 目标、无 TESTS 变量，configure.ac 无测试宏；tarball 内仅有 src/air10.c 与 manpage/metainfo"}\n'
exit 0
