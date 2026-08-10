cmake_minimum_required(VERSION 3.15)
project(imath_test_package LANGUAGES CXX)

find_package(Imath CONFIG REQUIRED)
add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Imath::Imath)
target_compile_features(test_package PRIVATE cxx_std_17)
