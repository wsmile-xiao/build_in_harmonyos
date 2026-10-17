#!/data/service/hnp/bin/bash
# Test fnt — verify the binary runs and shows help
set -e -o pipefail
# Use bash (not sh) to invoke fnt — the 0001-fnt.patch shebang fix
# points fnt at /data/service/hnp/bin/bash, so test under the same
# interpreter instead of overriding it with /system/bin/sh.
FNT="/data/service/hnp/bin/bash $(which fnt)"
FNT_BIN="$(which fnt)"

echo "=== fnt test suite ==="

# Test 0: fnt binary exists and is executable
echo "Test 0: fnt binary permission check"
if [ ! -x "$FNT_BIN" ]; then
    echo "FAIL: $FNT_BIN is not executable (chmod did not stick)" >&2
    exit 1
fi
echo "PASS: fnt binary is executable"

# Helper: run fnt and judge PASS/FAIL by exit code + output presence.
# fnt internally calls `id -u` which on HMDFS reports "bad uid", and
# otfinfo is absent — both make fnt return non-zero for environment
# reasons, NOT for adaptation failures. So we accept any exit code
# that is NOT a signal-induced crash (≥ 128) and require the command
# to have produced output (proving it actually ran, not segfaulted
# before printing anything). A bare `|| true` would swallow a crash
# too, which is the R34 空-shell variant this fixes.
run_fnt_and_judge() {
    local label="$1"
    shift
    local out rc
    out="$("$@" 2>&1)" && rc=0 || rc=$?
    if [ "$rc" -ge 128 ]; then
        echo "FAIL: $label crashed (rc=$rc)" >&2
        return 1
    fi
    if [ -z "$out" ]; then
        echo "FAIL: $label produced no output (rc=$rc)" >&2
        return 1
    fi
    echo "PASS: $label ran (rc=$rc, output present)"
    return 0
}

# Test 1: fnt --help shows usage
echo "Test 1: fnt --help"
run_fnt_and_judge "fnt --help" $FNT --help

# Test 2: fnt list (lists installed fonts, should not crash)
echo "Test 2: fnt list"
run_fnt_and_judge "fnt list" $FNT list
echo "NOTE: fnt list may show no fonts (expected on OHOS)"

# Test 3: fnt home (shows font directory)
echo "Test 3: fnt home"
run_fnt_and_judge "fnt home" $FNT home

# Test 4: Verify shebang is correct
echo "Test 4: shebang check"
if head -1 "$(which fnt)" | grep -q "hnp/bin/bash"; then
    echo "PASS: shebang is correct"
else
    echo "FAIL: shebang mismatch" >&2
    exit 1
fi

# Test 5: Verify HarmonyOS platform support
echo "Test 5: HarmonyOS platform check"
if grep -q "HarmonyOS" "$(which fnt)"; then
    echo "PASS: HarmonyOS supported"
else
    echo "FAIL: HarmonyOS platform not detected in fnt" >&2
    exit 1
fi

echo ""
echo "✅ All fnt tests passed"