#!/usr/bin/env python3
"""Conan test_package for html5lib — R34 real API usage (no empty shell).

html5lib is pure Python. The verifiable artifact is
lib/python3.12/site-packages/html5lib/ under <pkg>/. This test loads the
packaged module via PYTHONPATH and parses a real HTML document with
html5lib.parse(), asserting the parsed tree — proving the module is
loadable and functional.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    if not os.path.isfile(os.path.join(site, "html5lib", "__init__.py")):
        print(f"FAIL: html5lib/__init__.py not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)
    # 注入运行时依赖 six + webencodings 的 site-packages
    for dep_pkg in sys.argv[2:]:
        dep_site = os.path.join(dep_pkg, "lib", "python3.12", "site-packages")
        if os.path.isdir(dep_site):
            sys.path.insert(0, dep_site)
    try:
        import html5lib
    except Exception as e:
        print(f"FAIL: import html5lib: {e}", file=sys.stderr)
        return 1

    # R34: parse a real HTML document and assert the parsed tree.
    from html5lib import HTMLParser
    from html5lib.treebuilders import getTreeBuilder
    parser = HTMLParser(tree=getTreeBuilder("dom"))
    dom = parser.parse("<html><body><p>hello</p></body></html>")
    p = dom.getElementsByTagName("p")
    text = "".join(c.nodeValue for c in p[0].childNodes) if p else ""
    if not p or "hello" not in text:
        print("FAIL: parsed <p>hello</p> not found in DOM", file=sys.stderr)
        return 1
    print(f"OK: html5lib {html5lib.__version__} loaded, parse ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
