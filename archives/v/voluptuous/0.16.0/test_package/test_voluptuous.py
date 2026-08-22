#!/usr/bin/env python3
"""voluptuous consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — voluptuous.Schema validation
(pure user-space).

Usage: test_voluptuous.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "voluptuous")):
        raise AssertionError(f"voluptuous package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    from voluptuous import Schema

    schema = Schema({"name": str, "age": int})
    data = schema({"name": "test", "age": 30})
    if data["name"] != "test" or data["age"] != 30:
        raise AssertionError(f"Schema validation failed: {data}")
    print(f"OK: voluptuous 0.16.0 (Schema validate ok: "
          f"{data['name']}/{data['age']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
