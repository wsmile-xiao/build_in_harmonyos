"""test_frozenlist.py — consumer test for frozenlist 1.8.0.

Verifies the frozenlist package installed by the conan package is importable
and its FrozenList core API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import frozenlist

mod_path = os.path.realpath(frozenlist.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"frozenlist imported from {mod_path}, not from package {site}")

fl = frozenlist.FrozenList([1, 2, 3])
assert len(fl) == 3 and fl[0] == 1

print(frozenlist.__name__)
