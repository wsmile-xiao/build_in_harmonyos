#!/usr/bin/env python3
"""Conan test_package for tomli-w — R34 real API usage (no empty shell).

tomli-w is pure Python. The verifiable artifact is the tomli_w package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged tomli_w
and actually dumps a dict to a TOML string — proving the package is
functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "tomli_w")):
        print(f"FAIL: tomli_w package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import tomli_w

    # R34: dump a dict to TOML string and assert the output
    out = tomli_w.dumps({"title": "TOML Example", "owner": {"name": "Tom"}})
    if "title = \"TOML Example\"" not in out or "name = \"Tom\"" not in out:
        print(f"FAIL: tomli_w.dumps output unexpected:\n{out}",
              file=sys.stderr)
        return 1

    print(f"OK: tomli_w imported from package; dumps ->\n{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
