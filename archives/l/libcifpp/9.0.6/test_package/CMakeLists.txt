cmake_minimum_required(VERSION 3.23)
project(test_package CXX)

find_package(cifpp CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE cifpp::cifpp)
target_compile_features(test_package PRIVATE cxx_std_20)
