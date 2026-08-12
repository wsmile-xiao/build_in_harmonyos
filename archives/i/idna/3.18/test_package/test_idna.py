"""test_idna.py — consumer test for idna 3.18.

Verifies the idna package installed by the conan package is importable
and its core encode API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import idna

mod_path = os.path.realpath(idna.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"idna imported from {mod_path}, not from package {site}")

enc = idna.encode("example.com")
assert enc in (b"example.com", "example.com"), enc

print(idna.__name__)
