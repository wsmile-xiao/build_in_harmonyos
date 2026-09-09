cmake_minimum_required(VERSION 3.15)
project(test_c_list C)

find_package(c-list REQUIRED)

add_executable(test_c_list test_c_list.c)
target_link_libraries(test_c_list PRIVATE c-list::c-list)
