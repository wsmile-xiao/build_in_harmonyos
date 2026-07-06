#!/bin/sh
# test_package/test.sh — sponge functional test
# This script documents the test performed by test_package/conanfile.py
#
# Test 1: Basic write — soak up stdin and write to file
#   echo "hello from sponge" | sponge outfile && cat outfile
#   Expected: hello from sponge
#
# Test 2: No args — stdin to stdout
#   echo "pipe through" | sponge
#   Expected: pipe through
echo "sponge test package - functional verification"
