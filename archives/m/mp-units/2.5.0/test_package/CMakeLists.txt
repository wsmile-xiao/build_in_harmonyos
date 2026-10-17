cmake_minimum_required(VERSION 3.25)
project(test_package LANGUAGES CXX)

find_package(mp-units CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_20)
target_link_libraries(test_package PRIVATE mp-units::mp-units)
