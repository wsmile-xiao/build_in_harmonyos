cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(ghc-filesystem REQUIRED)

add_executable(test_package test_ghc_filesystem.cpp)
target_link_libraries(test_package PRIVATE ghc_filesystem)
target_compile_features(test_package PRIVATE cxx_std_17)