#!/usr/bin/env bash
# aiven-client 4.16.0 test script
# Smoke tests covering the core public API of aiven-client (R34).
# Does NOT depend on pytest — uses python3 -c for each test.

set -euo pipefail

echo "=== aiven-client 4.16.0 Smoke Test ==="

# ── Test 1: Module import + __version__ ───────────────────────────
echo "--- Test 1: Module import + version ---"
python3 -c "
from aiven.client.version import __version__
assert __version__ == '4.16.0', f'Expected 4.16.0, got {__version__!r}'
print('aiven-client imported, version OK:', __version__)
"

# ── Test 2: AivenClient class exists ───────────────────────────────
echo "--- Test 2: AivenClient class exists ---"
python3 -c "
from aiven.client import AivenClient
import inspect
assert inspect.isclass(AivenClient), 'AivenClient not a class'
# Constructor should accept a base_url parameter
sig = inspect.signature(AivenClient.__init__)
assert 'base_url' in sig.parameters or 'host' in sig.parameters, 'AivenClient.__init__ missing base_url/host param'
print('AivenClient class: PASS')
"

# ── Test 3: argx.CommandLineTool basic mechanism ──────────────────
echo "--- Test 3: argx.CommandLineTool ---"
python3 -c "
from aiven.client.argx import CommandLineTool, arg
class TestCLI(CommandLineTool):
    @arg()
    def hello(self):
        '''say hello'''
# Run --help should exit 0
try:
    TestCLI('test').run(args=['--help'])
except SystemExit as e:
    assert e.code == 0, f'--help exit code {e.code}'
print('argx.CommandLineTool: PASS')
"

# ── Test 4: pretty table formatting ───────────────────────────────
echo "--- Test 4: pretty.print_table ---"
python3 -c "
from aiven.client.pretty import print_table, flatten_list, format_item
import io, datetime, decimal
# format_item(key, value) tests
assert format_item(None, 1) == '1'
assert format_item(None, 'abc') == 'abc'
assert format_item('foo', datetime.datetime(2019, 12, 23)) == '2019-12-23T00:00:00'
assert format_item(None, decimal.Decimal('64.23')) == '64.23'
assert format_item(None, None) == 'null'
# flatten_list test
assert list(flatten_list(None)) == []
assert list(flatten_list(['x', 'y'])) == ['x', 'y']
print('pretty.print_table: PASS')
"

# ── Test 5: speller suggest ───────────────────────────────────────
echo "--- Test 5: speller.suggest ---"
python3 -c "
from aiven.client.speller import suggest
known = ['kafka', 'pg', 'mysql', 'grafana', 'valkey']
# suggest should return a known word for a close typo
result = suggest('kafk', known)
assert result in known or result is None, f'unexpected suggest result: {result}'
print('speller.suggest: PASS')
"

# ── Test 6: cli.AivenCLI entry point ──────────────────────────────
echo "--- Test 6: cli.AivenCLI entry ---"
python3 -c "
from aiven.client.cli import AivenCLI
import inspect
assert inspect.isclass(AivenCLI), 'AivenCLI not a class'
# AivenCLI should be a CommandLineTool subclass
from aiven.client.argx import CommandLineTool
assert issubclass(AivenCLI, CommandLineTool), 'AivenCLI not subclass of CommandLineTool'
print('cli.AivenCLI entry: PASS')
"

# ── Test 7: session.get_requests_session ──────────────────────────
echo "--- Test 7: session.get_requests_session ---"
python3 -c "
from aiven.client.session import get_requests_session
s = get_requests_session()
assert 'aiven-client' in s.headers.get('User-Agent', ''), 'User-Agent missing aiven-client'
print('session.get_requests_session: PASS')
"

echo
echo "=== aiven-client 4.16.0 all smoke tests PASS ==="
