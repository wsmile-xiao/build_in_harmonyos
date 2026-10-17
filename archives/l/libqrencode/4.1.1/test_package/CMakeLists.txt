cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libqrencode REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package libqrencode::libqrencode)

enable_testing()
add_test(NAME test_package COMMAND test_package)
