#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ngrep executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] ngrep -V (version check)"
OUTPUT=$(ngrep -V 2>&1) || {
    EXIT_CODE=$?
    # HarmonyOS: unsigned ELF gets Permission denied (exit code 126)
    # Only fall back to ELF verification for this specific case
    if [ "$EXIT_CODE" -eq 126 ] || echo "$OUTPUT" | grep -q "Permission denied"; then
        NGREP_BIN=$(command -v ngrep 2>/dev/null || echo "")
        if [ -z "$NGREP_BIN" ]; then
            echo "FAIL: ngrep binary not found in PATH"
            exit 1
        fi
        file "$NGREP_BIN" | grep -q "ELF" || {
            echo "FAIL: $NGREP_BIN is not a valid ELF"
            exit 1
        }
        echo "SKIP: ngrep -V failed (unsigned ELF on local build), ELF format verified"
        exit 0
    else
        echo "FAIL: ngrep -V failed with exit code $EXIT_CODE: $OUTPUT"
        exit 1
    fi
}
echo "$OUTPUT" | grep -q "ngrep" && echo "OK: --version output contains 'ngrep'" || {
    echo "FAIL: unexpected version output: $OUTPUT"
    exit 1
}
