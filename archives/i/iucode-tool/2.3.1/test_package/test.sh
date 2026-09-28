#!/data/service/hnp/bin/bash
# Real consumer test for the packaged iucode_tool executable.
set -eu

bin="${IUCODE_TOOL_BIN:-iucode_tool}"
pass=0
fail=0

run_case() {
    label="$1"
    shift
    out=""
    rc=0
    out="$($bin "$@" 2>&1)" || rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "✅ ${label} OK"
        pass=$((pass + 1))
    else
        echo "❌ ${label} FAIL (exit ${rc})"
        echo "$out"
        fail=$((fail + 1))
    fi
}

run_case_expect_text() {
    label="$1"
    expected="$2"
    shift 2
    out=""
    rc=0
    out="$($bin "$@" 2>&1)" || rc=$?
    if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -F "$expected" >/dev/null 2>&1; then
        echo "✅ ${label} OK"
        pass=$((pass + 1))
    else
        echo "❌ ${label} FAIL (exit ${rc})"
        echo "$out"
        fail=$((fail + 1))
    fi
}

# Assertion 1: packaged executable reports the selected upstream version.
run_case_expect_text "iucode_tool --version" "iucode_tool 2.3.1" --version
# Assertion 2: executable enters its arm64-safe system-scan path and reports
# that direct x86 CPUID inspection is unavailable.
run_case_expect_text "iucode_tool --scan-system" \
    "direct CPUID scan unavailable on this architecture" --scan-system
# Assertion 3: list mode is a real command path and handles an empty input set.
run_case "iucode_tool --list" --list

echo "[test] iucode-tool consumer smoke: pass=${pass} fail=${fail}"
if [ "$fail" -ne 0 ]; then
    exit 1
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"pass\":${pass},\"fail\":${fail},\"command\":\"bash test.sh\"}"
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"The official v2.3.1 source tree has no tests/ or test/ directory, no TESTS/check_PROGRAMS definition, and its generated make check target is an empty Automake no-op; the three consumer assertions above are not counted as upstream tests."}'
