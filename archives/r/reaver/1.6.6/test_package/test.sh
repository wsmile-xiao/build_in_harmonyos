#!/system/bin/sh
# test_package/test.sh — reaver 1.6.6 smoke test
#
# Verifies that reaver and wash binaries are installed, executable,
# and respond to --help / -h with expected usage text.
# The help commands may return non-zero exit code (binary quirk);
# this script judges pass/fail by output content, not exit code.

set -euo pipefail

BIN_DIR="$1"
PASS=0
FAIL=0

check_binary() {
    local name="$1"
    local path="$BIN_DIR/$name"
    if [ -f "$path" ] && [ -x "$path" ]; then
        echo "[PASS] $name exists and is executable"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $name not found or not executable at $path"
        FAIL=$((FAIL + 1))
    fi
}

check_help() {
    local name="$1"
    local path="$BIN_DIR/$name"
    local keywords="$2"
    local output
    local matched=0
    local kw_count=0

    # Try --help first, then -h
    output=$("$path" --help 2>&1) || output=$("$path" -h 2>&1) || true

    for kw in $keywords; do
        kw_count=$((kw_count + 1))
        case "$output" in
            *"$kw"*) matched=$((matched + 1)) ;;
        esac
    done

    if [ "$matched" -ge 1 ]; then
        echo "[PASS] $name --help/-h output contains expected keywords ($matched/$kw_count matched)"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $name --help/-h output missing expected keywords (got $matched/$kw_count)"
        echo "  --- output (first 10 lines) ---"
        echo "$output" | head -10
        echo "  ---"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== reaver 1.6.6 smoke test ==="
echo "Binary directory: $BIN_DIR"
echo ""

# 1. Check binaries exist and are executable
check_binary reaver
check_binary wash

# 2. Check help output contains expected keywords
# reaver keywords: usage, reaver, options, Example
check_help reaver "usage reaver options Example"

# wash keywords: usage, wash, options
check_help wash "usage wash options"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0