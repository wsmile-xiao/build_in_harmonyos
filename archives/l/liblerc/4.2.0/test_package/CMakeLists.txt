cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(liblerc REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE liblerc::liblerc)
target_compile_features(test_package PRIVATE cxx_std_11)
