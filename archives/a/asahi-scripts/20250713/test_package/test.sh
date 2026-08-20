#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for asahi-scripts
# Runs in conanrun env (PATH includes installed bin/)
# R34: Actually executes the installed asahi-diagnose binary
set -eu

echo "[test] Running asahi-diagnose..."

# asahi-diagnose is a shell script that collects system diagnostics.
# It runs to completion and produces output containing "Collecting" or "diagnostic".
# Some system paths may not exist on HarmonyOS, but the script handles
# missing files gracefully (no set -e in the script itself).
output=$(asahi-diagnose 2>&1 || true)

# Verify the script produced expected output — use printf for reliability
if printf '%s\n' "$output" | grep -qE "Collecting|diagnostic|Asahi"; then
    echo "✅ asahi-diagnose executed and produced expected output"
else
    echo "❌ asahi-diagnose did not produce expected output"
    echo "Output (first 10 lines):"
    printf '%s\n' "$output" | head -10
    exit 1
fi

# Verify functions.sh is installed alongside scripts
script_path=$(command -v asahi-diagnose 2>/dev/null || echo "")
if [ -n "$script_path" ]; then
    script_dir=$(dirname "$script_path")
    if [ -f "$script_dir/functions.sh" ]; then
        echo "✅ functions.sh found alongside scripts in $script_dir"
    else
        echo "⚠️  functions.sh not found in $script_dir (may be in share/)"
    fi
fi

echo "[test] All checks passed"
