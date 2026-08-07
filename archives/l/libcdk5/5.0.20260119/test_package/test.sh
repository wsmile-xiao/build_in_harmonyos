#!/bin/sh
# test_package test script for cdk 5.0.20260119
#
# Runs the Conan-built test_cdk binary and the installed cdk5-config helper.
# This script is invoked by the test_package conanfile.py test() method as a
# documented wrapper; the actual assertions live in test_cdk.c (CDKVersion()
# call + vSWINDOW enum inspection + link against -lcdkw -lncursesw).
set -e

# Test 1: run the compiled test_cdk binary (calls CDK API symbols)
"./test_cdk"

# Test 2: validate the installed cdk5-config helper script version output
cdk5-config --version

echo "test.sh: ALL CDK TESTS PASSED"
