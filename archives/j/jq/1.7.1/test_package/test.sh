#!/bin/sh
# test.sh — jq functional test
# Tests JSON processing, array mapping, and regex (oniguruma) support
set -e

# Test 1: JSON field extraction
RESULT=$(printf '%s' '{"name":"test","value":123}' | jq -r '.name')
if [ "$RESULT" != "test" ]; then
    echo "FAIL: field extraction returned '$RESULT', expected 'test'"
    exit 1
fi

# Test 2: Array mapping
RESULT=$(printf '%s' '[1,2,3]' | jq -c 'map(.*2)')
if [ "$RESULT" != "[2,4,6]" ]; then
    echo "FAIL: array mapping returned '$RESULT', expected '[2,4,6]'"
    exit 1
fi

# Test 3: Regex (oniguruma) support — key test for full functionality
RESULT=$(printf '%s' '"hello world"' | jq 'test("hel.*world")')
if [ "$RESULT" != "true" ]; then
    echo "FAIL: regex test returned '$RESULT', expected 'true'"
    exit 1
fi

# Test 4: String operations
RESULT=$(printf '%s' '{"a":1,"b":2}' | jq -c 'keys')
if [ "$RESULT" != '["a","b"]' ]; then
    echo "FAIL: keys returned '$RESULT', expected '[\"a\",\"b\"]'"
    exit 1
fi

echo "All jq tests passed"
