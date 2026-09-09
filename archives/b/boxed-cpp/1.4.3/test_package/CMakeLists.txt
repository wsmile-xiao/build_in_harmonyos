cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(boxed-cpp REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE boxed-cpp::boxed-cpp)
target_compile_features(test_package PRIVATE cxx_std_20)
