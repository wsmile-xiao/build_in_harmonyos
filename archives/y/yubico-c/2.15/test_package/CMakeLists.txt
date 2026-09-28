cmake_minimum_required(VERSION 3.15)
project(test_yubico-c C)

find_package(yubico-c REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package yubico-c::yubico-c)

enable_testing()
add_test(NAME test_package COMMAND test_package)
