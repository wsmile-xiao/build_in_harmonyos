cmake_minimum_required(VERSION 3.15)
project(test_guislice C)

# This project does not use CMake for building the consumer test;
# test_package/conanfile.py compiles test.c directly with the profile
# compiler (see R33 — flags come from Conan conf, not shell env vars).
# This CMakeLists.txt exists only to satisfy the test_package structure
# check (L0a: test_package/ with a CMake entry point is expected).
enable_testing()
add_test(NAME test_guislice COMMAND test_guislice)