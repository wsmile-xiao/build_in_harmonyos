cmake_minimum_required(VERSION 3.15)
project(test_str C)

find_package(str CONFIG REQUIRED)

add_executable(test_str test_str.c)
target_link_libraries(test_str PRIVATE str::str)
