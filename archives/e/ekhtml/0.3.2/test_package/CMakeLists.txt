cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(ekhtml REQUIRED)

add_executable(test_ekhtml test.c)
target_link_libraries(test_ekhtml PRIVATE ekhtml::ekhtml)
