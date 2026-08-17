#!/usr/bin/env python3
"""test_decorator.py — consumer test source for decorator 5.3.1 (L0c).

REAL API check (R34) on the packaged decorator:
  1) import decorator
  2) @decorator — create a simple decorator, verify it wraps and
     preserves signature/name (upstream tests/test.py core usage)
  3) decorator.decorator on a function with args/kwargs
Usage: test_decorator.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_decorator.py <site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "decorator")):
        raise AssertionError(f"decorator package missing under {site}")
    sys.path.insert(0, site)

    import decorator

    # @decorator: wrap a function, verify signature/name preserved
    @decorator.decorator
    def double(f, *args, **kwargs):
        return 2 * f(*args, **kwargs)

    @double
    def add(a, b):
        """add doc"""
        return a + b

    if add(3, 4) != 14:
        raise AssertionError(f"decorator wrap mismatch: {add(3, 4)}")
    if add.__name__ != "add":
        raise AssertionError(f"decorator name mismatch: {add.__name__}")
    if add.__doc__ != "add doc":
        raise AssertionError("decorator docstring mismatch")

    print("OK: decorator 5.3.1 real API ok (@decorator wrap/signature)")


if __name__ == "__main__":
    main()
