cmake_minimum_required(VERSION 3.15)
project(test_hiredis C)

find_package(hiredis REQUIRED CONFIG)

add_executable(test_hiredis test_hiredis.c)
target_link_libraries(test_hiredis PRIVATE hiredis::hiredis)
