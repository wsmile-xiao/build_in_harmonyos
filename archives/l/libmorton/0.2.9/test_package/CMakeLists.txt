cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(libmorton REQUIRED)

add_executable(test_libmorton test_libmorton.cpp)
target_link_libraries(test_libmorton PRIVATE libmorton::libmorton)
set_property(TARGET test_libmorton PROPERTY CXX_STANDARD 11)
set_property(TARGET test_libmorton PROPERTY CXX_STANDARD_REQUIRED ON)