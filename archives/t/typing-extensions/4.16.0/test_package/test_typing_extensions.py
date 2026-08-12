"""test_typing_extensions.py — consumer test for typing-extensions 4.16.0.

Verifies the typing_extensions module installed by the conan package
is importable and its core typing API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import typing_extensions as te

# Verify module comes from the conan package (hard dependency, R34)
mod_path = os.path.realpath(te.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"typing_extensions imported from {mod_path}, not from package {site}")

# Core API check
assert hasattr(te, "Required") and hasattr(te, "NotRequired")

print(te.__name__)
