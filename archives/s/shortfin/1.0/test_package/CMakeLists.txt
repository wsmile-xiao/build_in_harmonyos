cmake_minimum_required(VERSION 3.15)
project(test_shortfin C)

# Simple test executable that verifies the build chain works
add_executable(test_shortfin test.c)

enable_testing()
add_test(NAME test_shortfin COMMAND test_shortfin)
