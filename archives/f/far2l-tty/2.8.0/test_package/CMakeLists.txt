cmake_minimum_required(VERSION 3.15)
project(test_far2l_tty CXX)

# This test_package verifies the far2l application binary (TTY flavour).
# far2l-tty is an application (not a library), so there is no library to link.
# The test verifies the binary exists and responds to --help.

add_executable(test_far2l_tty test_far2l_tty.cpp)

enable_testing()
add_test(NAME test_far2l_tty COMMAND test_far2l_tty)
