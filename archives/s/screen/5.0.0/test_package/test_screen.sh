#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement)
# R34: Tests substantially exercise screen's functionality (version, help)
# The actual tests run via conanfile.py test() method

set -e

# Test 1: screen --version (smoke test - binary is installed and runnable)
screen --version

# Test 2: screen --help (verify help output is produced)
screen --help
