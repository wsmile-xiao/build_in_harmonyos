cmake_minimum_required(VERSION 3.5)
project(test_quickjs C)

find_package(quickjs REQUIRED CONFIG)

add_executable(test_quickjs test.c)
target_link_libraries(test_quickjs PRIVATE quickjs::quickjs)
