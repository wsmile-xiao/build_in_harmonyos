cmake_minimum_required(VERSION 3.15)
project(test_arpoison C)

# arpoison is a command-line tool, not a library.
# The test verifies the binary is installed and runnable (R34).
add_executable(test_arpoison test.c)

enable_testing()
add_test(NAME test_arpoison COMMAND test_arpoison)
