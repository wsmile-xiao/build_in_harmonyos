#!/usr/bin/env python3
"""Conan test_package for dominate — R34 real API usage (no empty shell).

dominate is pure Python. The verifiable artifact is the dominate package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged dominate
and actually builds an HTML document with tags — proving the package is
functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "dominate")):
        print(f"FAIL: dominate package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    from dominate import document
    from dominate.tags import h1, p

    # R34: build a real HTML document via dominate tags
    doc = document(title="dominate test")
    with doc:
        h1("Hello")
        p("world")
    html = str(doc)
    for expected in ("<html>", "<head>", "<title>dominate test</title>",
                     "<h1>Hello</h1>", "<p>world</p>"):
        if expected not in html:
            print(f"FAIL: rendered HTML missing {expected!r}:\n{html}",
                  file=sys.stderr)
            return 1

    print(f"OK: dominate imported from package; rendered HTML:\n{html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
