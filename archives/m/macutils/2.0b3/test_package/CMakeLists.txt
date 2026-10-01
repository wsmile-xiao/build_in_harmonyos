cmake_minimum_required(VERSION 3.15)
project(test_macutils C)

# Consumer of the macutils command-line tools (no library to link): the
# program drives macunpack/binhex/hexbin/macstream/macsave found on PATH.
add_executable(test_macutils test_macutils.c)
set_target_properties(test_macutils PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
target_compile_definitions(test_macutils PRIVATE _POSIX_C_SOURCE=200809L)
