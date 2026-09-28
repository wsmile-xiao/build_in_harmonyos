cmake_minimum_required(VERSION 3.15)
project(test_easy_memory C)

find_package(easy_memory REQUIRED)

add_executable(test_easy_memory test.c)
target_link_libraries(test_easy_memory PRIVATE easy_memory::easy_memory)
