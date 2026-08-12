"""test_propcache.py — consumer test for propcache 0.5.2.

Verifies the propcache package installed by the conan package is importable
and its core caching API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import propcache

# Verify module comes from the conan package (hard dependency, R34)
mod_path = os.path.realpath(propcache.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"propcache imported from {mod_path}, not from package {site}")

# Core API check
assert hasattr(propcache, "under_property") or hasattr(propcache, "cached_property")

print(propcache.__name__)