cmake_minimum_required(VERSION 3.18)
project(taskflow_test_package CXX)

# The taskflow headers require C++20: upstream forces CMAKE_CXX_STANDARD 20
# with CMAKE_CXX_STANDARD_REQUIRED ON, and the headers use C++20 concepts and
# designated initializers. Taskflow::taskflow also propagates -std=c++20
# through cpp_info.cxxflags; the explicit setting here documents the
# requirement independently of the generator.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Taskflow REQUIRED CONFIG)

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE Taskflow::taskflow)
