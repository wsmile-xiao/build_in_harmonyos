#!/bin/sh
# test_package/test.sh — alloy-analyzer 6.2.0 L1 smoke test
#
# Called by test_package/conanfile.py test() method.
# Usage: test.sh <alloy_binary_path> [work_dir]
#
# Asserts:
#   1. bin/alloy wrapper exists and is executable
#   2. libexec/*.jar (official Alloy JAR) is present
#   3. wrapper contains the HarmonyOS os.name=Linux override
#   4. `alloy version` prints "6.2.0"
#   5. `alloy commands` lists the commands declared in an Alloy model
#   6. `alloy exec` solves an Alloy model and writes receipt.json
set -euo pipefail

ALLOY="$1"
WORK_DIR="${2:-.}"
cd "$WORK_DIR"

# ── Prepare an Alloy model ─────────────────────────────────────────────
cat > hello.als <<'EOF'
module hello
sig Person { }
pred show { #Person = 2 }
run show for 3
EOF

# ── Assertion 1: wrapper exists and is executable ──────────────────────
echo "=== Assertion 1: bin/alloy exists and is executable ==="
if [ -f "$ALLOY" ] && [ -x "$ALLOY" ]; then
    echo "OK: bin/alloy exists and is executable"
else
    echo "FAIL: bin/alloy missing or not executable"
    exit 1
fi

# ── Assertion 2: libexec/*.jar present ─────────────────────────────────
echo "=== Assertion 2: libexec/alloy JAR exists ==="
LIBEXEC="$(cd "$(dirname "$ALLOY")/.." && pwd)/libexec"
JAR_COUNT=$(ls "$LIBEXEC"/org.alloytools.alloy.dist*.jar 2>/dev/null | wc -l)
if [ "$JAR_COUNT" -gt 0 ]; then
    echo "OK: found $JAR_COUNT alloy JAR(s) in libexec/"
else
    echo "FAIL: no alloy JAR found in libexec/"
    exit 1
fi

# ── Assertion 3: wrapper has os.name override ──────────────────────────
echo "=== Assertion 3: wrapper has -Dos.name=Linux override ==="
if grep -q 'Dos.name=Linux' "$ALLOY"; then
    echo "OK: wrapper contains -Dos.name=Linux override"
else
    echo "FAIL: wrapper missing -Dos.name=Linux override"
    exit 1
fi

# ── Assertion 4: alloy version ─────────────────────────────────────────
echo "=== Assertion 4: alloy version ==="
VERSION_OUTPUT="$("$ALLOY" version 2>&1 | grep -v '^Picked up')"
echo "version output: $VERSION_OUTPUT"
if echo "$VERSION_OUTPUT" | grep -q "6.2.0"; then
    echo "OK: alloy version = 6.2.0"
else
    echo "FAIL: version is not 6.2.0"
    exit 1
fi

# ── Assertion 5: alloy commands ────────────────────────────────────────
echo "=== Assertion 5: alloy commands ==="
COMMANDS_OUTPUT="$("$ALLOY" commands hello.als 2>&1 | grep -v '^Picked up')"
echo "commands output: $COMMANDS_OUTPUT"
if echo "$COMMANDS_OUTPUT" | grep -q "show"; then
    echo "OK: commands listed (show)"
else
    echo "FAIL: commands did not list 'show'"
    exit 1
fi

# ── Assertion 6: alloy exec solves the model ───────────────────────────
echo "=== Assertion 6: alloy exec solves the model ==="
rm -rf hello
# kodkod 在 aarch64 无原生库时向 stderr 输出 ERROR kodkod 噪声，此处仅过滤噪声；
# 真正判据是下方 [ -f hello/receipt.json ]（exec 真失败则不生成 receipt.json）
"$ALLOY" exec hello.als 2>&1 | grep -v '^Picked up' | grep -v 'ERROR kodkod' || true
if [ -f hello/receipt.json ]; then
    echo "OK: exec produced hello/receipt.json"
else
    echo "FAIL: exec did not produce hello/receipt.json"
    exit 1
fi

echo ""
echo "All alloy-analyzer smoke tests passed (6/6)"

# hmbs evidence marker — test_package result
echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh <alloy_bin> <work_dir>","assertions_passed":6,"assertions_total":6}'
