#!/usr/bin/env python3
"""jmespath consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — jmespath.search() on a real
expression (pure user-space).

Usage: test_jmespath.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "jmespath")):
        raise AssertionError(f"jmespath package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    import jmespath

    data = {"foo": {"bar": "baz"}, "a": [1, 2, 3]}
    r = jmespath.search("foo.bar", data)
    if r != "baz":
        raise AssertionError(f"unexpected search result: {r!r}")
    r2 = jmespath.search("a[1]", data)
    if r2 != 2:
        raise AssertionError(f"unexpected index result: {r2!r}")
    r3 = jmespath.search("length(a)", data)
    if r3 != 3:
        raise AssertionError(f"unexpected length result: {r3!r}")
    print(f"OK: jmespath 1.1.0 (search foo.bar + a[1] + length ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
