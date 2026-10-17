cmake_minimum_required(VERSION 3.15)
project(test_nnn C)

# nnn is a CLI tool (application), not a library — do NOT link against it.

add_executable(test_nnn test.c)
enable_testing()
add_test(NAME test_nnn COMMAND test_nnn)
