#!/usr/bin/env bash
# pyparsing 3.1.4 test script
# Verifies module import, version, and basic parsing functionality (R34)

set -euo pipefail

echo "=== pyparsing 3.1.4 L1 Smoke Test ==="

# Test 1: Module import and version
echo "--- Test 1: Module import ---"
python3 -c "
import pyparsing
print('pyparsing version:', pyparsing.__version__)
assert pyparsing.__version__ == '3.1.4', f'Expected 3.1.4, got {pyparsing.__version__}'
"

# Test 2: Basic word parsing
echo "--- Test 2: Basic word parsing ---"
python3 -c "
from pyparsing import Word, alphas, nums, ParseException
word = Word(alphas)
result = word.parse_string('hello')
assert result[0] == 'hello', 'Basic word parsing failed: expected hello, got %s' % result[0]
print('Word parsing: PASS (result: %s)' % result)
"

# Test 3: ParseException on invalid input
echo "--- Test 3: ParseException on invalid input ---"
python3 -c "
import sys
from pyparsing import Word, alphas, nums, ParseException
word = Word(alphas)
try:
    word.parse_string('123')
    print('ERROR: Expected ParseException')
    sys.exit(1)
except ParseException as e:
    print('ParseException correctly raised: %s' % str(e).split('\n')[0])
"

# Test 4: DOT-style grammar - simple graph node
echo "--- Test 4: DOT-style node parsing ---"
python3 -c "
from pyparsing import Word, alphas, nums, Literal, Optional, Group, Suppress, delimited_list
node_id = Word(alphas + '_', alphas + nums + '_')
node_stmt = node_id('name')
result = node_stmt.parse_string('node1')
assert result.name == 'node1', 'Node parsing failed'
print('DOT node parsing: PASS (name: %s)' % result.name)
dl = delimited_list(Word(alphas), ',')
result2 = dl.parse_string('a,b,c')
assert len(result2) == 3, 'delimited_list parsing failed: expected 3 items, got %d' % len(result2)
print('delimited_list parsing: PASS (items: %s)' % result2.asList())
"

# Test 5: Key-value attribute
echo "--- Test 5: Attribute parsing ---"
python3 -c "
from pyparsing import Word, alphas, alphanums, Literal, Suppress, Group
key = Word(alphas)
value = Word(alphanums)
kv_pair = Group(key('key') + Suppress(Literal('=')) + value('value'))
result = kv_pair.parse_string('label=center')
assert result[0].key == 'label'
assert result[0].value == 'center'
print('Attribute parsing: PASS (key=%s, value=%s)' % (result[0].key, result[0].value))
"

echo ""
echo "=== All tests PASSED ==="
