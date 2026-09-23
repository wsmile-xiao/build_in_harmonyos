#!/usr/bin/env python3
"""Run the official multipledispatch 1.0.0 tests without pytest.

The target Conan Python is intentionally minimal and does not ship pytest.
This runner supplies only the pytest decorators/fixture surface used by the
official tests, then executes the same test functions and parameter cases.
"""
import importlib.util
import inspect
import sys
import types
from pathlib import Path


class _Mark:
    def parametrize(self, names, values):
        names = tuple(name.strip() for name in names.split(","))

        def decorate(function):
            function._multipledispatch_parameters = (names, list(values))
            return function

        return decorate


def _fixture(function):
    return function


def _install_pytest_stub():
    pytest = types.ModuleType("pytest")
    pytest.mark = _Mark()
    pytest.fixture = _fixture
    sys.modules["pytest"] = pytest


def _benchmark(callable_object, *args, **kwargs):
    return callable_object(*args, **kwargs)


def _load_module(path, index):
    name = f"_multipledispatch_upstream_test_{index}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _cases(function):
    parameter_data = getattr(function, "_multipledispatch_parameters", None)
    if parameter_data is None:
        return [()]
    names, values = parameter_data
    cases = []
    for value in values:
        if len(names) == 1:
            value = (value,)
        elif not isinstance(value, tuple):
            raise TypeError(f"invalid parameter value for {function.__name__}")
        cases.append(value)
    return cases


def main():
    test_root = Path(__file__).resolve().parent / "multipledispatch" / "tests"
    _install_pytest_stub()
    passed = 0
    failed = []
    for index, path in enumerate(sorted(test_root.glob("test_*.py"))):
        module = _load_module(path, index)
        for name, function in module.__dict__.items():
            if not inspect.isfunction(function):
                continue
            if not name.startswith("test_"):
                continue
            for case_index, case in enumerate(_cases(function), 1):
                arguments = dict(zip(
                    getattr(function, "_multipledispatch_parameters", ((), []))[0],
                    case,
                ))
                for parameter in inspect.signature(function).parameters:
                    if parameter == "benchmark":
                        arguments[parameter] = _benchmark
                label = f"{path.name}::{name}"
                if len(_cases(function)) > 1:
                    label += f"[{case_index}]"
                try:
                    function(**arguments)
                except Exception as error:
                    failed.append((label, error))
                else:
                    passed += 1

    print(f"upstream functional tests: {passed} passed, {len(failed)} failed")
    for label, error in failed:
        print(f"FAIL {label}: {type(error).__name__}: {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
