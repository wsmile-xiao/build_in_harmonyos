cmake_minimum_required(VERSION 3.5)
project(test_package CXX)

find_package(RTTR CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE RTTR::Core)
