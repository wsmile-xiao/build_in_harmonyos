cmake_minimum_required(VERSION 3.5)
project(test_zlog C)

find_package(zlog REQUIRED CONFIG)

add_executable(test_zlog test_zlog.c)
target_link_libraries(test_zlog PRIVATE zlog::zlog)