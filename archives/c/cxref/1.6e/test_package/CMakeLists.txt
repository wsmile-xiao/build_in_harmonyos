cmake_minimum_required(VERSION 3.15)
project(test_cxref C)

# cxref is a CLI tool, not a library — there is nothing to link against.
# test_cxref receives the path of the installed cxref binary as argv[1] from
# test_package/conanfile.py test(), runs it on a sample C file, and asserts
# the generated cross reference, the usage banner and the error path.
# Testing is driven by Conan, not CTest.

add_executable(test_cxref test_cxref.c)
