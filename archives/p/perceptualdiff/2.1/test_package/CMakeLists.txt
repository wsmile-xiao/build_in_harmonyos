cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(perceptualdiff REQUIRED)

add_executable(test_probe test.cpp)
target_link_libraries(test_probe perceptualdiff::perceptualdiff)
