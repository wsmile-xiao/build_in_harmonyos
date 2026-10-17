cmake_minimum_required(VERSION 3.15)
project(test_lib60870 C)

find_package(lib60870 REQUIRED CONFIG)

add_executable(test_lib60870 test.c)
target_link_libraries(test_lib60870 PRIVATE lib60870::lib60870)
