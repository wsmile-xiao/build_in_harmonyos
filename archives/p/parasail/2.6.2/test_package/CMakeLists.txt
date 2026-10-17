cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(parasail REQUIRED)

enable_testing()
add_executable(test_package test.c)
target_link_libraries(test_package parasail::parasail)
add_test(NAME parasail_test COMMAND test_package)
