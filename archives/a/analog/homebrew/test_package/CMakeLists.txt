cmake_minimum_required(VERSION 3.15)
project(test_analog C)

# Test package: analog is an application package (not a library).
# test.c calls analog --version and --help via system() to verify
# the binary is installed and executable.

add_executable(test_analog test.c)
# No external libraries to link — analog is a standalone binary.

enable_testing()
add_test(NAME test_analog_compile COMMAND test_analog)