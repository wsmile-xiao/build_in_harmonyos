cmake_minimum_required(VERSION 3.15)
project(test_far2l CXX)

# This test_package verifies the far2l application binary.
# far2l is an application (not a library), so there is no library to link.
# The test verifies the binary exists and responds to --help.

add_executable(test_far2l test_far2l.cpp)

enable_testing()
add_test(NAME test_far2l COMMAND test_far2l)
