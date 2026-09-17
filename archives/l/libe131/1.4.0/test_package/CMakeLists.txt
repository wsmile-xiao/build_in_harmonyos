cmake_minimum_required(VERSION 3.15)

project(test_libe131 C)

find_package(libe131 CONFIG REQUIRED)

add_executable(test_libe131 test.c)

target_link_libraries(test_libe131 PRIVATE libe131::libe131)
