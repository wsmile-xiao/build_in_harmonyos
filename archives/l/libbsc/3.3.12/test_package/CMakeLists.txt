cmake_minimum_required(VERSION 3.24)
project(test_package C CXX)

find_package(libbsc REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE libbsc::libbsc)
