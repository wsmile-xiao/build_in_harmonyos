cmake_minimum_required(VERSION 3.15)
project(test_libntru LANGUAGES C)

find_package(libntru REQUIRED CONFIG)

add_executable(test_libntru test.c)
target_link_libraries(test_libntru PRIVATE libntru::libntru)
