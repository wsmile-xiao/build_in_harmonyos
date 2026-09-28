cmake_minimum_required(VERSION 3.12)
project(test_libmicrodns C)

find_package(libmicrodns REQUIRED CONFIG)

add_executable(test_libmicrodns test_libmicrodns.c)
target_link_libraries(test_libmicrodns libmicrodns::libmicrodns)
