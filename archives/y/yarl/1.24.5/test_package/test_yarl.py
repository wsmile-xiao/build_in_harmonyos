"""test_yarl.py — consumer test for yarl 1.24.5.

Verifies the yarl package installed by the conan package is importable
and its core URL API works (requires idna/multidict/propcache from deps).
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path[0:0] = site.split(os.pathsep)

import yarl

mod_path = os.path.realpath(yarl.__file__)
site_dirs = [os.path.realpath(s) for s in site.split(os.pathsep)] if site else []
if site_dirs and not any(
    mod_path == s or mod_path.startswith(s + os.sep) for s in site_dirs
):
    raise AssertionError(f"yarl imported from {mod_path}, not from package {site}")

u = yarl.URL("https://example.com/path?q=1")
assert u.scheme == "https"
assert u.host == "example.com"
assert str(u).startswith("https://")

print(yarl.__name__)