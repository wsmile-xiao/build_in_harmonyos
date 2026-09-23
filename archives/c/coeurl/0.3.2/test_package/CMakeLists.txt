cmake_minimum_required(VERSION 3.15)
project(test_coeurl CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(coeurl REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package coeurl::coeurl)

enable_testing()
add_test(NAME test_package COMMAND test_package)
