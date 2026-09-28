cmake_minimum_required(VERSION 3.15)
project(test_libconvolve C)

find_package(libconvolve REQUIRED)
add_executable(test_libconvolve test.c)
target_link_libraries(test_libconvolve PRIVATE libconvolve::libconvolve)
