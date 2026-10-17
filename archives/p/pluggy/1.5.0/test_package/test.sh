#!/usr/bin/env bash
# pluggy 1.5.0 test script
# Smoke tests covering the core public API of pluggy (R34).
# Does NOT depend on pytest — uses python3 -c for each test.

set -euo pipefail

echo "=== pluggy 1.5.0 Smoke Test ==="

# ── Test 1: Module import + __version__ ───────────────────────────
echo "--- Test 1: Module import + version ---"
python3 -c "
import pluggy
from pluggy import __version__
assert __version__ == '1.5.0', f'Expected 1.5.0, got {__version__!r}'
print('pluggy imported, version OK:', __version__)
"

# ── Test 2: HookspecMarker/HookimplMarker decorators exist ─────────
echo "--- Test 2: HookspecMarker/HookimplMarker exist ---"
python3 -c "
from pluggy import HookspecMarker, HookimplMarker
import inspect
assert callable(HookspecMarker), 'HookspecMarker not callable'
assert callable(HookimplMarker), 'HookimplMarker not callable'
print('HookspecMarker/HookimplMarker: PASS')
"

# ── Test 3: PluginManager register + hook call (1:N) ───────────────
echo "--- Test 3: PluginManager register + hook call ---"
python3 -c "
import pluggy
hookspec = pluggy.HookspecMarker('myproject')
hookimpl = pluggy.HookimplMarker('myproject')

class MySpec:
    @hookspec
    def myhook(self, arg1, arg2):
        pass

class Plugin_1:
    @hookimpl
    def myhook(self, arg1, arg2):
        return arg1 + arg2

class Plugin_2:
    @hookimpl
    def myhook(self, arg1, arg2):
        return arg1 - arg2

pm = pluggy.PluginManager('myproject')
pm.add_hookspecs(MySpec)
pm.register(Plugin_1())
pm.register(Plugin_2())
results = pm.hook.myhook(arg1=1, arg2=2)
assert 3 in results and -1 in results, f'Unexpected hook results: {results}'
assert len(results) == 2, f'Expected 2 results, got {len(results)}'
print('PluginManager register + hook call 1:N: PASS', results)
"

# ── Test 4: add_hookspecs + call_historic ─────────────────────────
echo "--- Test 4: add_hookspecs + call_historic ---"
python3 -c "
import pluggy
hookspec = pluggy.HookspecMarker('historic')
hookimpl = pluggy.HookimplMarker('historic')

class HSpec:
    @hookspec(historic=True)
    def h(self, arg):
        pass

class HImpl:
    def __init__(self):
        self.calls = []
    @hookimpl
    def h(self, arg):
        self.calls.append(arg)

pm = pluggy.PluginManager('historic')
pm.add_hookspecs(HSpec)
impl = HImpl()
pm.register(impl)
# pluggy 1.5.0: call_historic(result_callback=None, kwargs=None)
pm.hook.h.call_historic(kwargs={'arg': 'before'})
pm.hook.h.call_historic(kwargs={'arg': 'after'})
assert impl.calls == ['before', 'after'], f'Unexpected historic calls: {impl.calls}'
print('add_hookspecs + call_historic: PASS', impl.calls)
"

# ── Test 5: hook result flattening (result wrapper) ────────────────
echo "--- Test 5: hook result flattening ---"
python3 -c "
import pluggy
hookspec = pluggy.HookspecMarker('flatten')
hookimpl = pluggy.HookimplMarker('flatten')

class FSpec:
    @hookspec
    def f(self):
        pass

class FImpl:
    @hookimpl
    def f(self):
        return [1, 2, 3]

pm = pluggy.PluginManager('flatten')
pm.add_hookspecs(FSpec)
pm.register(FImpl())
results = pm.hook.f()
assert results == [[1, 2, 3]], f'Unexpected results: {results}'
print('hook result flattening: PASS')
"

# ── Test 6: tryfirst/trylast ordering ──────────────────────────────
echo "--- Test 6: tryfirst/trylast ordering ---"
python3 -c "
import pluggy
hookspec = pluggy.HookspecMarker('order')
hookimpl = pluggy.HookimplMarker('order')

class OSpec:
    @hookspec
    def o(self):
        pass

class First:
    @hookimpl(tryfirst=True)
    def o(self):
        return 'first'

class Middle:
    @hookimpl
    def o(self):
        return 'middle'

class Last:
    @hookimpl(trylast=True)
    def o(self):
        return 'last'

pm = pluggy.PluginManager('order')
pm.add_hookspecs(OSpec)
pm.register(Middle())
pm.register(Last())
pm.register(First())
results = pm.hook.o()
assert results == ['first', 'middle', 'last'], f'Unexpected ordering: {results}'
print('tryfirst/trylast ordering: PASS', results)
"

# ── Test 7: ValidationError on bad hook spec ───────────────────────
echo "--- Test 7: hook spec arg mismatch raises ---"
python3 -c "
import pluggy
hookspec = pluggy.HookspecMarker('mismatch')
hookimpl = pluggy.HookimplMarker('mismatch')

class MSpec:
    @hookspec
    def m(self, arg):
        pass

class MImpl:
    @hookimpl
    def m(self, wrong_arg):
        pass

pm = pluggy.PluginManager('mismatch')
pm.add_hookspecs(MSpec)
# pluggy 1.5.0: PluginValidationError is raised at register() time
# (_verify_hook), not at hook call time.
try:
    pm.register(MImpl())
    raise AssertionError('Expected PluginValidationError at register()')
except pluggy.PluginValidationError:
    print('hook spec arg mismatch raises PluginValidationError: PASS')
"

echo ""
echo "=== All 7 tests PASSED ==="
