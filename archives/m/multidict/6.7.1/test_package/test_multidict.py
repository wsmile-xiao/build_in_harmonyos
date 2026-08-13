"""test_multidict.py — consumer test for multidict 6.7.1.

Verifies the multidict package installed by the conan package is importable
and its core MultiDict API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import multidict

mod_path = os.path.realpath(multidict.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"multidict imported from {mod_path}, not from package {site}")

md = multidict.MultiDict()
md.add("k", 1)
md.add("k", 2)
assert md.getall("k") == [1, 2]
assert len(md) == 2

print(multidict.__name__)