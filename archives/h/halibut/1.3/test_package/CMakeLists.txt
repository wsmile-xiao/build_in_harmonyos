cmake_minimum_required(VERSION 3.15)
project(test_halibut C)

# For application packages, we test the binary via system() calls.
# No need to find_package or link against the application.

add_executable(test_halibut test.c)

enable_testing()
add_test(NAME test_halibut COMMAND test_halibut)