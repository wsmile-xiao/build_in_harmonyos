cmake_minimum_required(VERSION 3.15)
project(test_hexcurse C)

# Simple test: verify hexcurse binary exists and prints version
add_executable(test_hexcurse test.c)
enable_testing()
add_test(NAME test_hexcurse COMMAND test_hexcurse)
