cmake_minimum_required(VERSION 3.15)
project(test_snow C)

# snow is package_type="application" — no library to link.
# The test binary invokes `snow` via system() relying on PATH
# (set by Conan's conanrun env).

add_executable(test_snow test.c)

enable_testing()
add_test(NAME test_snow COMMAND test_snow)
