#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for pixiewps executable
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `pixiewps`).
# pixiewps -V and -h exit with ARG_ERROR(3) by design; this script verifies the
# output strings explicitly rather than relying on a zero exit code.
set -euo pipefail

bin="pixiewps"

if ! command -v "$bin" >/dev/null 2>&1; then
    echo "❌ pixiewps executable not found: $bin"
    exit 1
fi

# --- Test 1: pixiewps -V (version output) ---
# -V prints "Pixiewps <LONG_VERSION>" to stdout then returns ARG_ERROR(3).
rc=0
out=$("$bin" -V 2>&1) || rc=$?

# Expected exit codes: 0 (future change) or 3 (ARG_ERROR, current by-design behavior)
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "[fail] pixiewps -V exited with unexpected code $rc (expected 0 or 3)"
    echo "$out"
    exit 1
fi

case "$out" in
    *"Pixiewps 1.4.2"*)
        echo "[ok] pixiewps -V: version string 'Pixiewps 1.4.2' verified"
        ;;
    *)
        echo "[fail] pixiewps -V: version string 'Pixiewps 1.4.2' not found in output"
        echo "$out"
        exit 1
        ;;
esac

# --- Test 2: pixiewps -h (usage screen) ---
# -h prints the usage screen to stderr then returns ARG_ERROR(3).
rc=0
out=$("$bin" -h 2>&1) || rc=$?

if [ "$rc" -ne 3 ]; then
    echo "[fail] pixiewps -h exited with unexpected code $rc (expected 3)"
    echo "$out"
    exit 1
fi

case "$out" in
    *"Usage"*)
        echo "[ok] pixiewps -h: usage screen verified"
        ;;
    *)
        echo "[fail] pixiewps -h: usage text not found in output"
        echo "$out"
        exit 1
        ;;
esac

echo "[done] all smoke tests passed"
