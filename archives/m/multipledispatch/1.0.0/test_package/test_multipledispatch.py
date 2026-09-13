#!/usr/bin/env python3
"""Standalone consumer smoke test for multipledispatch 1.0.0."""
import importlib.metadata
import os
import sys


def main():
    if len(sys.argv) != 1:
        raise AssertionError("test_multipledispatch.py takes no arguments")

    import multipledispatch
    from multipledispatch import Dispatcher, dispatch

    assert importlib.metadata.version("multipledispatch") == "1.0.0"
    assert multipledispatch.__version__ == "0.6.0"

    @dispatch(int, int)
    def combine(left, right):
        return left + right

    @dispatch(str, str)
    def combine(left, right):
        return left + ":" + right

    assert combine(2, 3) == 5
    assert combine("left", "right") == "left:right"

    custom = Dispatcher("custom")
    custom.add((int,), lambda value: value + 1)
    assert custom(4) == 5
    try:
        combine(1, "right")
    except NotImplementedError:
        pass
    else:
        raise AssertionError("unregistered signature unexpectedly dispatched")

    print("multipledispatch/1.0.0 consumer smoke test passed")


if __name__ == "__main__":
    main()
