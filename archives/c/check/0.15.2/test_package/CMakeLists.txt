cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(check REQUIRED)

add_executable(test_check test.c)
target_link_libraries(test_check PRIVATE Check::check)
