"""Minimal `pytest` compatibility shim (pure Python, stdlib only).

Why this exists
---------------
cfgv 3.4.0's upstream test suite ``tests/cfgv_test.py`` targets the
``pytest`` framework.  On HarmonyOS PC the test_package cannot install
pytest from PyPI (no outbound network), so the upstream suite would
otherwise run 0/71 tests and trip rule-4 condition-2 ("upstream tests
not run").

This shim implements *only* the three pytest APIs the upstream suite
actually uses — ``pytest.raises``, ``pytest.fixture`` and
``pytest.mark.parametrize`` — enough for a stdlib ``unittest`` runner
to execute all 71 upstream test functions verbatim.  No pytest package
is required; the shim is imported as ``pytest`` from the bridge runner.

Implemented API surface
------------------------
- ``pytest.raises(ExpectedException)`` — context manager; on exit
  stores the caught exception on ``.value`` (mirrors pytest).  Raises
  ``AssertionError`` if the expected exception is not raised.
- ``pytest.fixture`` — decorator marking a generator function as a
  fixture; the bridge runner drives the generator to obtain/teardown
  the fixture value.
- ``pytest.mark.parametrize(argnames, argvalues)`` — decorator that
  appends one ``(names_tuple, values_list)`` entry per call to the
  function's ``_pytest_params`` list.  The bridge runner computes the
  cartesian product across multiple parametrize decorators on the same
  function (pytest semantics) and merges the resulting kwargs.

Out of scope (not used by upstream cfgv_test.py): ``pytest.skip``,
``pytest.xfail``, ``pytest.mark.skip/xfail``, plugins, hooks.
"""
import contextlib

__all__ = ['raises', 'fixture', 'mark']


class _RaisesContext:
    """Context manager mirroring pytest.raises(exc).value."""

    def __init__(self, expected_exception):
        self.expected_exception = expected_exception
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(
                f'Did not raise {self.expected_exception!r}'
            )
        if not issubclass(exc_type, self.expected_exception):
            return False  # let unexpected exceptions propagate
        self.value = exc_val
        return True  # swallow the expected exception


def raises(expected_exception, *args, **kwargs):
    """pytest.raises shim — assert an exception is raised."""
    return _RaisesContext(expected_exception)


def fixture(func=None, *args, **kwargs):
    """pytest.fixture shim — mark a generator function as a fixture."""
    def _decorate(f):
        f._pytest_fixture = True
        return f
    if func is None:
        return _decorate
    return _decorate(func)


class _Mark:
    """pytest.mark shim namespace — only parametrize is exercised."""

    @staticmethod
    def parametrize(argnames, argvalues, *args, **kwargs):
        def _decorate(func):
            if isinstance(argnames, str):
                names = tuple(n.strip() for n in argnames.split(',') if n.strip())
            else:
                names = tuple(argnames)
            values = list(argvalues)
            existing = getattr(func, '_pytest_params', [])
            # Append this decorator's (names, values) entry.
            func._pytest_params = existing + [(names, values)]
            return func

        return _decorate


mark = _Mark
