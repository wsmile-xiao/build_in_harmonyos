#!/usr/bin/env python3
"""Test: Verify CMake HTML documentation is properly installed.

This test checks that the cmake-docs Conan package contains the expected
HTML documentation files built from the CMake source tree using Sphinx.
"""
import os
import sys
import glob


def main():
    pkg_root = os.environ.get("PACKAGE_ROOT", "")
    if not pkg_root:
        print("ERROR: PACKAGE_ROOT environment variable not set")
        sys.exit(1)

    # Find index.html in the package
    html_files = glob.glob(
        os.path.join(pkg_root, "**", "html", "index.html"),
        recursive=True,
    )
    if not html_files:
        print("ERROR: CMake HTML documentation (index.html) not found in package")
        sys.exit(1)

    doc_dir = os.path.dirname(html_files[0])
    print(f"Found CMake documentation at: {doc_dir}")

    # Verify key documentation files
    required_files = ["index.html", "searchindex.js", "genindex.html"]
    for f in required_files:
        path = os.path.join(doc_dir, f)
        if not os.path.isfile(path):
            print(f"ERROR: {f} not found")
            sys.exit(1)
        print(f"  {f}: OK")

    print("CMake documentation test: PASS")


if __name__ == "__main__":
    main()
