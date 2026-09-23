cmake_minimum_required(VERSION 3.15)
project(test_sasa C)

# sasa is a CLI tool, not a library — do NOT link against it.
# The test binary receives the socket-activate path as a command-line
# argument from the Conan test_package conanfile.py test() method.
# Testing is driven by Conan, not CTest.

add_executable(test_sasa test.c)
