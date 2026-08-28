#!/data/service/hnp/bin/bash
# test_package/test.sh — boids 2.0.0 consumer verification
# Runs inside the conanrun environment: NODE_PATH points at the installed
# boids package root (set by the recipe's runenv_info).  The actual
# functional assertions live in test.js (17 cases).
set -euo pipefail

echo "[test] boids module resolution check"

NODE_BIN=$(command -v node || echo "")
if [ -z "$NODE_BIN" ]; then
    echo "FAIL: node not found in PATH"
    exit 1
fi
echo "OK: node $($NODE_BIN --version)"

NODE_PATH_VAL="${NODE_PATH:-}"
if [ -z "$NODE_PATH_VAL" ]; then
    echo "FAIL: NODE_PATH is not set (recipe runenv_info did not propagate)"
    exit 1
fi
echo "OK: NODE_PATH=$NODE_PATH_VAL"

# The packaged module must contain the entry point, npm manifest, license and readme
MODULE_DIR="$NODE_PATH_VAL/boids"
for f in index.js package.json LICENSE.md README.md; do
    if [ ! -f "$MODULE_DIR/$f" ]; then
        echo "FAIL: missing packaged module file boids/$f"
        exit 1
    fi
done
echo "OK: boids module files present"

# The single runtime dependency (inherits) must be bundled
if [ ! -f "$NODE_PATH_VAL/node_modules/inherits/inherits.js" ]; then
    echo "FAIL: runtime dependency node_modules/inherits is not bundled"
    exit 1
fi
echo "OK: runtime dependency inherits bundled"

# Run the 17-case functional test suite against the installed module
echo "[test] running functional test suite (test.js)"
"$NODE_BIN" "$(dirname "$0")/test.js"

echo "All tests passed."