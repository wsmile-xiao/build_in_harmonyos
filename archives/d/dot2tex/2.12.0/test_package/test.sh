#!/usr/bin/env bash
# test_package/test.sh — smoke test for dot2tex executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "==========================================="
echo "dot2tex 2.12.0 smoke test"
echo "==========================================="

# Test 1: --version
echo "[test] dot2tex --version"
dot2tex --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    dot2tex --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ dot2tex failed both --version and --help"
        exit 1
    }
}

# Test 2: Python module import (do NOT rely on dot2tex.__version__, upstream may not export it)
echo "[test] python3 -c 'import dot2tex'"
python3 -c "
import dot2tex
print('✅ Module imported: dot2tex')
print(f'   Package location: {dot2tex.__file__}')
" || {
    echo "❌ Python module import failed"
    exit 1
}

# Test 3: DOT 语法解析（dotparsing，纯 Python）
# 完整 DOT→TikZ 转换依赖外部 graphviz `dot` 命令，OHOS 环境无该工具，
# 故用 dot2tex.dotparsing（pyparsing 驱动、纯 Python）真实解析 DOT 语法，
# 验证被测包核心 API 可用（R34）。
echo "[test] Basic DOT parsing via dot2tex.dotparsing"
python3 -c "
import sys
from dot2tex import dotparsing

parser = dotparsing.DotDataParser()
dot_source = 'digraph G { a -> b; }'
try:
    graph = parser.parse_dot_data(dot_source)
except Exception as e:
    print(f'❌ dotparsing.parse_dot_data() raised an exception: {e!r}')
    print('   This usually means a runtime dependency (e.g. pyparsing) is')
    print('   missing from PYTHONPATH, or the DOT input is invalid.')
    sys.exit(1)

if graph is None:
    print('❌ Parsing returned None')
    sys.exit(1)
print(f'✅ DOT parsing succeeded: {type(graph).__name__}')
"

echo ""
echo "==========================================="
echo "All dot2tex smoke tests completed"
echo "==========================================="
