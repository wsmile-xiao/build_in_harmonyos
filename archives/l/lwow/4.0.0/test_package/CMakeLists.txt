cmake_minimum_required(VERSION 3.22)
project(test_package C)

enable_testing()

find_package(lwow REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE lwow::lwow)

add_test(NAME test_package COMMAND test_package)