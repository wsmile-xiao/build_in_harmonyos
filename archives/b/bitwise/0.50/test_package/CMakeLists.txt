cmake_minimum_required(VERSION 3.15)
project(test_bitwise C)

# bitwise is a CLI tool, not a library — do NOT link against it.
# The test binary receives the bitwise path as a command-line argument
# from the Conan test_package conanfile.py test() method.
# Testing is driven by Conan, not CTest.

add_executable(test_bitwise test.c)
