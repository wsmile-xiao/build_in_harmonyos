cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libgphoto2 REQUIRED)
find_package(libtool REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package libgphoto2::libgphoto2 libtool::libtool)
