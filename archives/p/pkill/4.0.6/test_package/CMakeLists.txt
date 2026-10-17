cmake_minimum_required(VERSION 3.15)
project(test_pkill C)

# pkill is a binary tool — no library to link against
# PKILL_BIN is passed from conanfile.py with the full path to the pkill binary

add_executable(test_pkill test.c)
target_compile_definitions(test_pkill PRIVATE PKILL_BIN="${PKILL_BIN}")

enable_testing()
add_test(NAME test_pkill COMMAND test_pkill)
