cmake_minimum_required(VERSION 3.15)
project(test_base-installer C)

add_executable(test_base-installer test.c)

enable_testing()
add_test(NAME test_base-installer COMMAND test_base-installer)