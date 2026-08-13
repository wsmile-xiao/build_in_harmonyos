"""test_aiohappyeyeballs.py — consumer test for aiohappyeyeballs 2.7.1.

Verifies the aiohappyeyeballs package installed by the conan package
is importable and its core API works.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import aiohappyeyeballs

mod_path = os.path.realpath(aiohappyeyeballs.__file__)
if site and not mod_path.startswith(os.path.realpath(site)):
    raise AssertionError(f"aiohappyeyeballs imported from {mod_path}, not from package {site}")

assert hasattr(aiohappyeyeballs, "addr_to_addr_infos")
assert hasattr(aiohappyeyeballs, "start_connection")

print(aiohappyeyeballs.__name__)
