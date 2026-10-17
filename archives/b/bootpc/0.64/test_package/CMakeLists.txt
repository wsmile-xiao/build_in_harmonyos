cmake_minimum_required(VERSION 3.15)
project(test_bootpc C)

add_executable(test_bootpc test.c)
target_link_libraries(test_bootpc PRIVATE bootpc)
