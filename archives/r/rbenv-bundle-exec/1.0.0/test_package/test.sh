#!/usr/bin/env bash
# test_package/test.sh — rbenv-bundle-exec file existence and syntax check
set -euo pipefail

# Plugin directory passed as first argument from conanfile.py
PLUGIN_DIR="${1:?Usage: test.sh <plugin_dir>}"

# Test 1: plugin directory exists
test -d "$PLUGIN_DIR"

# Test 2: bundle-exec.bash hook script exists
test -f "$PLUGIN_DIR/etc/rbenv.d/exec/bundle-exec.bash"

# Test 3: LICENSE file exists
test -f "$PLUGIN_DIR/LICENSE"

# Test 4: bash syntax check on hook script
bash -n "$PLUGIN_DIR/etc/rbenv.d/exec/bundle-exec.bash"

echo "All rbenv-bundle-exec tests PASSED"
