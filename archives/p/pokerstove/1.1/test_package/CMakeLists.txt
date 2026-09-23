cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pokerstove REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE pokerstove::pokerstove)

enable_testing()
add_test(NAME pokerstove_consumer_test COMMAND test_package)
