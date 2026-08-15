cmake_minimum_required(VERSION 3.16)
project(test_gd C)

find_package(gd REQUIRED CONFIG)

add_executable(test_gd test_gd.c)
target_link_libraries(test_gd PRIVATE gd::gd)

enable_testing()
add_test(NAME test_gd COMMAND test_gd)
