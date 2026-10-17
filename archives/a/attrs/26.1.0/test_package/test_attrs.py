"""test_attrs.py — consumer test for attrs 26.1.0.

Verifies the attr package installed by the conan package is importable
and its core attr.make_class API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import attr

mod_path = os.path.realpath(attr.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"attr imported from {mod_path}, not from package {site}")

C = attr.make_class("Point", ["x", "y"])
p = C(1, 2)
assert p.x == 1 and p.y == 2

print(attr.__name__, C.__name__)
