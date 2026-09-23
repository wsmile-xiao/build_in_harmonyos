cmake_minimum_required(VERSION 3.15)
project(cpp_gsl_test_package LANGUAGES CXX)

find_package(Microsoft.GSL CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Microsoft.GSL::GSL)
target_compile_features(test_package PRIVATE cxx_std_14)
