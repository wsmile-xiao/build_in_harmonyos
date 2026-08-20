cmake_minimum_required(VERSION 3.15)
project(test_zlib C)

find_package(zlib REQUIRED)

add_executable(test_zlib test.c)
target_link_libraries(test_zlib zlib::zlib)

add_library(zlib_pic_probe SHARED pic_probe.c)
target_link_libraries(zlib_pic_probe zlib::zlib)
