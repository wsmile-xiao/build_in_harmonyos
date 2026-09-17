cmake_minimum_required(VERSION 3.15)
project(test_libjpeg6b C)

find_package(libjpeg6b REQUIRED)

add_executable(test_libjpeg6b test.c)
target_link_libraries(test_libjpeg6b libjpeg6b::libjpeg6b)
