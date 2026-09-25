cmake_minimum_required(VERSION 3.15)
project(mecab_jumandic_test CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mecab CONFIG REQUIRED)

add_executable(test_package src/test_package.cpp)
target_link_libraries(test_package PRIVATE mecab::mecab)
