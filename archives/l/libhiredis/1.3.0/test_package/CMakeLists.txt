cmake_minimum_required(VERSION 3.15)
project(test_libhiredis C)

find_package(hiredis REQUIRED CONFIG)

add_executable(test_libhiredis test_libhiredis.c)
target_link_libraries(test_libhiredis PRIVATE hiredis::hiredis)
