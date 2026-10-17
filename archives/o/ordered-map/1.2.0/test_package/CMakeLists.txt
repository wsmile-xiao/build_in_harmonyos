cmake_minimum_required(VERSION 3.15)
project(test_ordered_map CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ordered-map REQUIRED)

add_executable(test_ordered_map test.cpp)
target_link_libraries(test_ordered_map ordered-map::ordered-map)
