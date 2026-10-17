#!/usr/bin/env bash
# identify 2.6.19 test script
# Verifies module import, version, and basic file type identification API (R34)
# 注：identify 上游 __init__.py 是空文件，模块不导出 __version__；
# 文件类型识别 API（tags_from_path/tags_from_filename/tags_from_interpreter/
# file_is_text/ALL_TAGS）定义在 identify.identify 子模块，
# 上游测试用 `from identify import identify` 访问（见 tests/identify_test.py:14）。

set -euo pipefail

echo "=== identify 2.6.19 L1 Smoke Test ==="

# Test 1: Module import and version
echo "--- Test 1: Module import ---"
python3 -c "
import identify
from identify import identify as _identify
from importlib.metadata import version
v = version('identify')
print('identify version:', v)
assert v == '2.6.19', f'Expected 2.6.19, got {v}'
# API 路径确认：tags_from_path 等函数在 identify.identify 子模块
assert hasattr(_identify, 'tags_from_path'), 'identify.identify.tags_from_path missing'
assert hasattr(_identify, 'ALL_TAGS'), 'identify.identify.ALL_TAGS missing'
print('API path OK')
"

# Test 2: tags_from_path on a directory
echo "--- Test 2: tags_from_path (directory) ---"
python3 -c "
import os
from identify import identify
tags = identify.tags_from_path(os.getcwd())
assert 'directory' in tags, f'Expected directory tag, got {tags}'
print('Directory tags:', tags)
"

# Test 3: tags_from_path on a Python file
echo "--- Test 3: tags_from_path (Python file) ---"
python3 -c "
from identify import identify
import tempfile
import os
with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
    f.write('print(\"hello\")\n')
    path = f.name
try:
    tags = identify.tags_from_path(path)
    assert 'python' in tags, f'Expected python tag, got {tags}'
    assert 'text' in tags, f'Expected text tag, got {tags}'
    print('Python file tags:', tags)
finally:
    os.unlink(path)
"

# Test 4: tags_from_filename
echo "--- Test 4: tags_from_filename ---"
python3 -c "
from identify import identify
tags = identify.tags_from_filename('test.py')
assert 'python' in tags, f'Expected python tag for test.py, got {tags}'
print('test.py tags:', tags)
tags2 = identify.tags_from_filename('config.json')
assert 'json' in tags2, f'Expected json tag for config.json, got {tags2}'
print('config.json tags:', tags2)
tags3 = identify.tags_from_filename('Makefile')
# 上游对 Makefile 返回的 tag 是 'makefile'（见 identify/extensions.py），非 'make'
assert 'makefile' in tags3, f'Expected makefile tag for Makefile, got {tags3}'
print('Makefile tags:', tags3)
"

# Test 5: tags_from_interpreter
echo "--- Test 5: tags_from_interpreter ---"
python3 -c "
from identify import identify
tags = identify.tags_from_interpreter('python3')
assert 'python' in tags, f'Expected python tag for python3, got {tags}'
print('python3 interpreter tags:', tags)
tags2 = identify.tags_from_interpreter('/usr/bin/bash')
assert 'shell' in tags2, f'Expected shell tag for bash, got {tags2}'
print('bash interpreter tags:', tags2)
"

# Test 6: ALL_TAGS completeness
echo "--- Test 6: ALL_TAGS completeness ---"
python3 -c "
from identify import identify
assert 'directory' in identify.ALL_TAGS, 'directory missing from ALL_TAGS'
assert 'file' in identify.ALL_TAGS, 'file missing from ALL_TAGS'
assert 'python' in identify.ALL_TAGS, 'python missing from ALL_TAGS'
assert 'json' in identify.ALL_TAGS, 'json missing from ALL_TAGS'
print('ALL_TAGS count:', len(identify.ALL_TAGS))
print('ALL_TAGS completeness: PASS')
"

# Test 7: file_is_text
echo "--- Test 7: file_is_text ---"
python3 -c "
from identify import identify
import tempfile
import os
with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
    f.write('hello world\n')
    path = f.name
try:
    assert identify.file_is_text(path), f'Expected True for text file'
    print('file_is_text (text): PASS')
finally:
    os.unlink(path)
"

echo ""
echo "=== All tests PASSED ==="
