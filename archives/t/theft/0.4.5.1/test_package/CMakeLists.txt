cmake_minimum_required(VERSION 3.15)
project(theft_test C)

find_package(theft CONFIG REQUIRED)

add_executable(theft_test test.c)
target_link_libraries(theft_test PRIVATE theft::theft)
