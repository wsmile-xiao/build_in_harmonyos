cmake_minimum_required(VERSION 3.15)
project(test_pkill C)

# pkill is a binary tool — no library to link against
# We just verify the test compiles and runs

add_executable(test_pkill test.c)

enable_testing()
add_test(NAME test_pkill COMMAND test_pkill)
