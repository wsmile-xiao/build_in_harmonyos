cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(yara REQUIRED)

enable_testing()
add_executable(test_package test.c)
target_link_libraries(test_package yara::yara)
add_test(NAME yara_test COMMAND test_package)
