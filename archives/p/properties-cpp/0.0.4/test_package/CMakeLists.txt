cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(properties-cpp REQUIRED CONFIG)

add_executable(test_properties test_properties.cpp)
target_link_libraries(test_properties properties-cpp::properties-cpp)
set_property(TARGET test_properties PROPERTY CXX_STANDARD 11)
