#!/bin/sh
# test_ts.sh — smoke test for ts (ts-node) 10.9.2
# Verifies that the installed ts-node wrapper can execute real TypeScript:
#   1. ts-node --version outputs v10.9.2
#   2. a .ts file with type annotations compiles and runs
#   3. a type error is rejected (transpile-only must NOT be used, i.e. the
#      compiler is actually engaged)
# This file satisfies CI L0c (test source file requirement).
# The actual test execution is handled by test_package/conanfile.py test().

set -e

# HMDFS denies the exec bit on wrapper scripts (E087): resolve the bin path
# (TS_NODE_WRAPPER is injected by conanfile.py from dependency info) and
# invoke it through `sh` explicitly.
TS_NODE_BIN="${TS_NODE_BIN:-ts-node}"
run_ts() { sh "${TS_NODE_WRAPPER:-$TS_NODE_BIN}" "$@"; }

# Test 1: --version should output 10.9.2
output="$(run_ts --version 2>&1)"
echo "ts-node --version output: $output"
echo "$output" | grep -q "10.9.2" || {
    echo "FAIL: expected version 10.9.2 in output"
    exit 1
}

# Test 2: run a real TypeScript file (type annotations + const enum-free code)
cat > smoke.ts <<'EOF'
const answer: number = 40 + 2;
function greet(name: string): string {
    return `hello ${name}`;
}
if (answer !== 42) { process.exit(1); }
console.log(`ts-node-ok:${answer}:${greet("ohos")}`);
EOF
output="$(run_ts smoke.ts 2>&1)"
echo "ts-node smoke.ts output: $output"
echo "$output" | grep -q "ts-node-ok:42:hello ohos" || {
    echo "FAIL: expected ts-node-ok:42:hello ohos in output"
    exit 1
}

# Test 3: a type error must fail (proves the TypeScript compiler is engaged)
cat > bad.ts <<'EOF'
const n: number = "not a number";
EOF
if run_ts bad.ts >/dev/null 2>&1; then
    echo "FAIL: type error was not reported"
    exit 1
fi
echo "PASS: type error correctly rejected"

echo "PASS: ts-node --version returns 10.9.2 and TypeScript execution works"
