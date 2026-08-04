cmake_minimum_required(VERSION 3.15)
project(test_libdbi C)

find_package(libdbi CONFIG REQUIRED)

add_executable(test_libdbi test_libdbi.c)
target_link_libraries(test_libdbi PRIVATE libdbi::libdbi)
