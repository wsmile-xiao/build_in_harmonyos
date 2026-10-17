cmake_minimum_required(VERSION 3.16)
project(test_nuklear C)

find_package(nuklear REQUIRED CONFIG)

add_executable(test_nuklear test_nuklear.c)
target_link_libraries(test_nuklear PRIVATE nuklear::nuklear)
