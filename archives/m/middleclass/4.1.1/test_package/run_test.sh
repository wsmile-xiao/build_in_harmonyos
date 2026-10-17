#!/bin/sh
# run_test.sh — Shell wrapper for middleclass test_package
# Satisfies CI L0c (test source file detection: .sh extension)
# The actual test is orchestrated by conanfile.py test() method
lua "$(dirname "$0")/test.lua"
