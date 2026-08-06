#!/usr/bin/env python3
"""abs-guide 10 consumer test — verify packaged HTML documentation.

Asserts:
  1. share/doc/abs-guide/ exists in the package
  2. key pages (index.html / part1.html / copyright.html / xrefindex.html) exist
  3. total HTML page count is 140 (matches upstream tarball)
  4. every page is non-empty
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_abs_guide.py <package_folder>")
        return 2
    pkg = sys.argv[1]
    doc_dir = os.path.join(pkg, "share", "doc", "abs-guide")
    if not os.path.isdir(doc_dir):
        print(f"[fail] missing {doc_dir}")
        return 1

    pages = sorted(f for f in os.listdir(doc_dir) if f.endswith(".html"))
    expected = ["index.html", "part1.html", "copyright.html", "xrefindex.html"]
    missing = [e for e in expected if e not in pages]
    if missing:
        print(f"[fail] missing key pages: {missing}")
        return 1
    if len(pages) != 140:
        print(f"[fail] expected 140 HTML pages, got {len(pages)}")
        return 1
    for p in pages:
        fp = os.path.join(doc_dir, p)
        if os.path.getsize(fp) == 0:
            print(f"[fail] empty page: {p}")
            return 1
    print(f"[ok] abs-guide 10: {len(pages)} HTML pages verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
