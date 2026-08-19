#!/usr/bin/env python3
"""Bridge runner — executes upstream cfgv_test.py without pytest.

Why this exists
---------------
cfgv 3.4.0 ships ``tests/cfgv_test.py`` (71 test functions, pytest
framework).  HarmonyOS PC has no outbound PyPI access, so pytest
cannot be installed and the upstream suite would otherwise run 0/71
tests (rule-4 condition-2 failure).

This runner does NOT depend on pytest.  It loads the upstream test
module verbatim (the only import substitution is registering
``pytest_shim`` as the ``pytest`` module before import), expands
``@pytest.mark.parametrize`` decorators into one sub-test per
parameter tuple (computing the cartesian product across multiple
decorators on the same function, per pytest semantics), resolves
``@pytest.fixture`` generator fixtures for any test-function
parameter that matches a fixture name, and invokes every ``test_*``
function directly.  Pass/fail/error counts are tallied and a summary
line is printed.

Exit code is 0 iff all tests pass, non-zero otherwise.

Implemented upstream-API coverage
---------------------------------
- ``pytest.raises(Exc)`` context manager (``.value`` attribute)
- ``pytest.fixture`` decorator (generator-yield fixtures)
- ``pytest.mark.parametrize(argnames, argvalues)`` decorator
"""
import contextlib
import importlib.util
import inspect
import itertools
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
UPSTREAM_DIR = os.path.join(HERE, 'upstream')

# ── 1. Register the pytest shim as `pytest` BEFORE importing the
#       upstream test module, so `import pytest` resolves to our shim.
sys.path.insert(0, HERE)
import pytest_shim  # noqa: E402
sys.modules['pytest'] = pytest_shim


def _load_upstream_tests():
    """Load upstream tests/cfgv_test.py as a module and return it."""
    test_path = os.path.join(UPSTREAM_DIR, 'cfgv_test.py')
    spec = importlib.util.spec_from_file_location('cfgv_test', test_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_fixtures(module):
    """Return {fixture_name: fixture_func} for all @pytest.fixture funcs."""
    fixtures = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if getattr(obj, '_pytest_fixture', False):
            fixtures[name] = obj
    return fixtures


def _resolve_fixture_value(fixture_func):
    """Drive a fixture generator/return to obtain its value."""
    if inspect.isgeneratorfunction(fixture_func):
        gen = fixture_func()
        return next(gen)
    return fixture_func()


def _builtin_fixture(name):
    """Provide pytest built-in tmpdir/tmp_path fixtures via stdlib tempfile.

    - ``tmpdir``: a ``py.path.local``-like object in upstream tests; we
      return a ``TempDir`` shim exposing ``.strpath`` and ``/`` join so
      the ``test_load_from_filename_*`` tests resolve real on-disk paths.
    - ``tmp_path``: a ``pathlib.Path`` to a fresh temp directory.
    """
    import pathlib
    import tempfile

    if name == 'tmp_path':
        d = tempfile.mkdtemp(prefix='cfgv_tmp_')
        return pathlib.Path(d)
    if name == 'tmpdir':
        d = tempfile.mkdtemp(prefix='cfgv_tmp_')

        class _Local:
            """Minimal ``py.path.local`` shim for upstream cfgv tests.

            Exposes ``.strpath``, ``.join()``, ``__truediv__``,
            ``mkdir()`` and ``as_cwd()`` — the subset of the legacy
            ``tmpdir`` API the ``test_load_from_filename_*`` tests use.
            """

            def __init__(self, p):
                self._p = pathlib.Path(p)
                self.strpath = str(self._p)

            def __truediv__(self, other):
                return _Local(self._p / other)

            def __fspath__(self):
                return self.strpath

            def join(self, other):
                return _Local(self._p / other)

            def mkdir(self):
                self._p.mkdir(parents=True, exist_ok=True)
                return self

            def ensure_dir(self):
                return self.mkdir()

            def write(self, data, mode='w'):
                self._p.parent.mkdir(parents=True, exist_ok=True)
                with open(self._p, mode) as fh:
                    fh.write(data)
                return self

            def exists(self):
                return self._p.exists()

            def read(self, mode='r'):
                with open(self._p, mode) as fh:
                    return fh.read()

            @contextlib.contextmanager
            def as_cwd(self):
                prev = os.getcwd()
                os.chdir(self._p)
                try:
                    yield
                finally:
                    os.chdir(prev)

        return _Local(pathlib.Path(d))
    return None


def _expand_parametrize(func):
    """Yield (display_name, kwargs) for a test func, expanding parametrize.

    pytest semantics: multiple ``@parametrize`` decorators on the same
    function are combined as a cartesian product, with each decorator
    contributing one (argnames, argvalues) entry.  The result is one
    sub-test per product element, with kwargs merged from each entry.
    """
    params = getattr(func, '_pytest_params', None)
    if not params:
        yield func.__name__, {}
        return

    # Build, per parametrize decorator, the list of kwargs dicts it
    # contributes.  For a single-name decorator the whole argvalues
    # element is that one argument (do NOT iterate a namedtuple).
    per_set = []
    for names, values in params:
        entries = []
        for vals in values:
            if len(names) == 1:
                entries.append({names[0]: vals})
            else:
                entries.append(dict(zip(names, vals)))
        per_set.append(entries)

    # Cartesian product across decorators (pytest semantics).
    for combo in itertools.product(*per_set):
        kw = {}
        for entry in combo:
            kw.update(entry)
        label = repr(combo)
        yield f'{func.__name__}[{label}]', kw


def run():
    """Execute all upstream test_* functions. Returns (passed, failed, errored, total)."""
    module = _load_upstream_tests()
    fixtures = _collect_fixtures(module)

    test_funcs = [
        obj for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith('test_')
    ]

    passed = 0
    failed = 0
    errored = 0
    total = 0

    for func in test_funcs:
        sig = inspect.signature(func)
        param_names = list(sig.parameters)
        for display, paramz_kwargs in _expand_parametrize(func):
            total += 1
            kwargs = dict(paramz_kwargs)
            # Resolve any remaining params from fixtures (builtin or @pytest.fixture).
            for pname in param_names:
                if pname in kwargs:
                    continue
                built = _builtin_fixture(pname)
                if built is not None:
                    kwargs[pname] = built
                elif pname in fixtures:
                    kwargs[pname] = _resolve_fixture_value(fixtures[pname])
            try:
                func(**kwargs)
                passed += 1
            except AssertionError:
                failed += 1
                print(f'FAIL  {display}')
                traceback.print_exc()
            except Exception as exc:  # noqa: BLE001 — any non-Assertion is an error
                errored += 1
                print(f'ERROR {display}: {exc!r}')
                traceback.print_exc()

    print()
    print(f'=== Upstream cfgv_test.py: {passed}/{total} passed, '
          f'{failed} failed, {errored} errored ===')
    return passed, failed, errored, total


if __name__ == '__main__':
    p, f, e, t = run()
    sys.exit(0 if (f == 0 and e == 0) else 1)
