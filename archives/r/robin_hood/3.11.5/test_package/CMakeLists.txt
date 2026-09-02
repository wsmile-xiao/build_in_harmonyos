cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(robin_hood REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package robin_hood::robin_hood)

enable_testing()
add_test(NAME test_package COMMAND test_package)
