cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(coordgen REQUIRED CONFIG)

add_executable(test_package example.cpp)
target_link_libraries(test_package PRIVATE coordgen::coordgen)
