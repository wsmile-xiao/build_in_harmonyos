cmake_minimum_required(VERSION 3.15)
project(test_libcrystalhd C)

find_package(libcrystalhd REQUIRED)

add_executable(test_libcrystalhd test.c)
target_link_libraries(test_libcrystalhd libcrystalhd::libcrystalhd)
