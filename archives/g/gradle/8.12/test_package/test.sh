#!/bin/sh
# test_package/test.sh — gradle 8.12 L1 package structure test
#
# Called by test_package/conanfile.py test() method.
# Usage: test.sh <package_folder>
#
# Tests that the packaged distribution has the expected structure:
#   1. bin/gradle wrapper script exists and is executable
#   2. lib/ directory contains JAR files
#   3. Wrapper script contains HarmonyOS-aware JAVA_TOOL_OPTIONS override
set -euo pipefail

PKG_DIR="$1"

# Assertion 1: bin/gradle exists and is executable
echo "=== Assertion 1: bin/gradle exists ==="
if [ -f "$PKG_DIR/bin/gradle" ] && [ -x "$PKG_DIR/bin/gradle" ]; then
    echo "✅ bin/gradle exists and is executable"
else
    echo "❌ bin/gradle missing or not executable"
    exit 1
fi

# Assertion 2: lib/ contains JAR files
echo "=== Assertion 2: lib/*.jar exists ==="
JAR_COUNT=$(ls "$PKG_DIR/lib/"*.jar 2>/dev/null | wc -l)
if [ "$JAR_COUNT" -gt 0 ]; then
    echo "✅ Found $JAR_COUNT JAR files in lib/"
else
    echo "❌ No JAR files found in lib/"
    exit 1
fi

# Assertion 3: wrapper script contains os.name override
echo "=== Assertion 3: wrapper has os.name override ==="
if grep -q 'Dos.name=Linux' "$PKG_DIR/bin/gradle"; then
    echo "✅ Wrapper contains -Dos.name=Linux override"
else
    echo "❌ Wrapper missing -Dos.name=Linux override"
    exit 1
fi

echo ""
echo "All gradle package structure tests passed"

# hmbs evidence marker — test_package result
echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh <package_folder>"}'