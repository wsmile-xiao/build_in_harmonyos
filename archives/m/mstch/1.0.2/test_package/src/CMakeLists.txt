cmake_minimum_required(VERSION 3.5...3.31)
project(test_package CXX)

find_package(mstch REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE mstch::mstch)
target_compile_features(test_package PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_package COMMAND test_package)
