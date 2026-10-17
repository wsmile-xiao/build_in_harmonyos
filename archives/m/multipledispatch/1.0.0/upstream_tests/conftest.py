"""Small fallback for the upstream benchmark fixture.

The official tests use pytest-benchmark for timing-oriented tests. The
adaptation disables that timing plugin during Conan builds and keeps the
functional assertions by executing the callable once.
"""
import pytest


@pytest.fixture
def benchmark():
    def run(callable_object, *args, **kwargs):
        return callable_object(*args, **kwargs)

    return run
