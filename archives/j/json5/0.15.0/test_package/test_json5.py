#!/usr/bin/env python3
"""Conan test_package for json5 — R34 real API usage (no empty shell).

json5 is pure Python. The verifiable artifact is the json5 package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged json5
and actually parses a JSON5 string (with comments + trailing commas, which
plain json cannot handle) — proving the package is functional, not just
present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "json5")):
        print(f"FAIL: json5 package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import json5

    # R34: parse a JSON5 string — comments + trailing comma (JSON5 features)
    data = json5.loads('{"a": 1, /* comment */ "b": [1, 2, 3,],}')
    if data != {"a": 1, "b": [1, 2, 3]}:
        print(f"FAIL: json5.loads returned {data!r}", file=sys.stderr)
        return 1

    print("OK: json5 imported from package; JSON5 parse (comment+trailing "
          "comma) ->", data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
