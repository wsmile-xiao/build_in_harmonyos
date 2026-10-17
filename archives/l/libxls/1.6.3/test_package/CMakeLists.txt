cmake_minimum_required(VERSION 3.15)
project(test_libxls C)

find_package(libxls REQUIRED CONFIG)

add_executable(test_libxls test_libxls.c)
target_link_libraries(test_libxls PRIVATE libxls::libxls)
