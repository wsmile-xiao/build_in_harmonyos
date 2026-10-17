cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

# graaf requires C++20 (uses concepts/requires clauses)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(graaf REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE graaf::graaf)
