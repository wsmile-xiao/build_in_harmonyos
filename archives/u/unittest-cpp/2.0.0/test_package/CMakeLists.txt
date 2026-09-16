cmake_minimum_required(VERSION 3.15)
project(unittest_cpp_test CXX)

find_package(UnitTest++ CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE UnitTest++)
