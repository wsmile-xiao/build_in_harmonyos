cmake_minimum_required(VERSION 3.15)
project(ntl_test LANGUAGES CXX)

find_package(ntl REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE ntl::ntl)
target_compile_features(test_package PRIVATE cxx_std_11)
