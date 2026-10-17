#!/usr/bin/env python3
"""Conan test_package for ranger.

Imports the ranger Python module and verifies the version,
then checks that the rifle entry-point script is available.
"""
# Add the package folder to PYTHONPATH (set by conan runenv)
import ranger

# Verify version
assert ranger.__version__ == "1.9.4", f"Expected 1.9.4, got {ranger.__version__}"
print(f"ranger version: {ranger.__version__}")

# Verify rifle module is accessible
from ranger.ext import rifle
print("rifle module imported successfully")

print("All tests passed!")
