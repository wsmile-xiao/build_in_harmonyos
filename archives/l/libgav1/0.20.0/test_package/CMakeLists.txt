cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(libgav1 CONFIG REQUIRED)

add_executable(test_package test.cpp)
target_link_libraries(test_package PRIVATE gav1::gav1)
