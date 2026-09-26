cmake_minimum_required(VERSION 3.15)
project(pystring_consumer LANGUAGES CXX)

find_package(pystring REQUIRED)

add_executable(test_pystring test.cpp)
target_link_libraries(test_pystring PRIVATE pystring::pystring)
