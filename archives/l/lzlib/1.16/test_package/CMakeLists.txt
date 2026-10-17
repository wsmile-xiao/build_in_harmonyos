cmake_minimum_required(VERSION 3.15)
project(test_lzlib C)

find_package(lzlib REQUIRED)

add_executable(test_lzlib test.c)
target_link_libraries(test_lzlib PRIVATE lzlib::lzlib)
