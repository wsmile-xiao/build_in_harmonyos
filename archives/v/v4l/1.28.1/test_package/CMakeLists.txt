cmake_minimum_required(VERSION 3.15)
project(test_v4l C)

find_package(v4l REQUIRED)

add_executable(test_v4l test_v4l.c)
target_link_libraries(test_v4l PRIVATE v4l::v4l)
