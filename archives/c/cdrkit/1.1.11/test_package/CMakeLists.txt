cmake_minimum_required(VERSION 3.15)
project(test_cdrkit C)

# Build the structure check binary
add_executable(test_cdrkit test.c)

enable_testing()
add_test(NAME cdrkit_structure_check COMMAND test_cdrkit)
