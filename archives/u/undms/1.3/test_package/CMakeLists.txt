cmake_minimum_required(VERSION 3.15)
project(test_undms C)

add_executable(test_undms test.c)
target_include_directories(test_undms PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_options(test_undms PRIVATE -static)
