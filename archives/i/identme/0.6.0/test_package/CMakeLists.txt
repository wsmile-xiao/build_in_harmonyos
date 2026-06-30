cmake_minimum_required(VERSION 3.15)
project(test_identme C)

# Simple smoke test - verify the package is installed
enable_testing()

# Create a trivial test executable
add_executable(test_identme test.c)

# The test just checks the binary compiles and runs
add_test(NAME test_identme COMMAND test_identme)
