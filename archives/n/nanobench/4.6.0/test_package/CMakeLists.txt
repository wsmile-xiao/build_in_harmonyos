cmake_minimum_required(VERSION 3.15)
project(test_nanobench CXX)

find_package(nanobench CONFIG REQUIRED)

add_executable(test_nanobench test.cpp)
target_link_libraries(test_nanobench PRIVATE nanobench::nanobench)
set_target_properties(test_nanobench PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
