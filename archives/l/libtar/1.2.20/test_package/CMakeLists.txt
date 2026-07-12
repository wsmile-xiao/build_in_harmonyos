cmake_minimum_required(VERSION 3.15)
project(test_libtar C)

find_package(libtar REQUIRED)

add_executable(test_libtar test.c)
target_link_libraries(test_libtar libtar::libtar)
