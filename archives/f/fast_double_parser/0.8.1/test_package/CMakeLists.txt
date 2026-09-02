cmake_minimum_required(VERSION 3.11)
project(fast_double_parser_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(fast_double_parser CONFIG REQUIRED)

add_executable(fast_double_parser_test test.cpp)
target_link_libraries(fast_double_parser_test PRIVATE fast_double_parser::fast_double_parser)
