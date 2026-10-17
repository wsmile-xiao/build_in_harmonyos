#!/bin/sh
# Test source file for p7zip test_package
# This script is referenced by test_package/MANIFEST.yml
# The actual test logic runs in conanfile.py test() method which
# executes the 7za binary to create, list, and test archives

echo "p7zip test_package smoke test"
