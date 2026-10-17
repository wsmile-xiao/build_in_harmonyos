#!/usr/bin/bash
# test.sh — Smoke test for secureboot-hook 0.2
# Verifies that the hook script and config file are installed correctly.
# The hook script cannot be fully executed (requires Void Linux + dracut + sbctl),
# but we verify file presence, permissions, and content.
set -euo pipefail

# First argument: path to the package's etc/kernel.d directory
KERNEL_D_DIR="$1"

HOOK_PATH="$KERNEL_D_DIR/post-install/30-secureboot"
CONF_PATH="$KERNEL_D_DIR/secureboot.conf"

# Test 1: Hook script exists and is executable
test -f "$HOOK_PATH"
test -x "$HOOK_PATH"
echo "Test 1 PASS: Hook script exists and is executable"

# Test 2: Config file exists
test -f "$CONF_PATH"
echo "Test 2 PASS: Config file exists"

# Test 3: Hook script has correct shebang
head -1 "$HOOK_PATH" | grep -q "#!/usr/bin/bash"
echo "Test 3 PASS: Hook script has correct shebang"

# Test 4: Config file contains expected settings
grep -q "output_dir" "$CONF_PATH"
grep -q "sign" "$CONF_PATH"
echo "Test 4 PASS: Config file contains expected settings"

# Test 5: Hook script references secureboot (content verification)
grep -q "secureboot" "$HOOK_PATH"
echo "Test 5 PASS: Hook script contains secureboot references"

echo "All secureboot-hook tests PASSED"
