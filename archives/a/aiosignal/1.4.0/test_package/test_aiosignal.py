"""test_aiosignal.py — consumer test for aiosignal 1.4.0.

Verifies the aiosignal package installed by the conan package is importable
and its core Signal API works (requires frozenlist from conan deps).
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path[0:0] = site.split(os.pathsep)

import aiosignal

mod_path = os.path.realpath(aiosignal.__file__)
site_dirs = [os.path.realpath(s) for s in site.split(os.pathsep)] if site else []
if site_dirs and not any(mod_path.startswith(s) for s in site_dirs):
    raise AssertionError(f"aiosignal imported from {mod_path}, not from package {site}")

assert hasattr(aiosignal, "Signal")

print(aiosignal.__name__)