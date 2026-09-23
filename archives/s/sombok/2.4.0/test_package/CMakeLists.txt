cmake_minimum_required(VERSION 3.15)
project(test_sombok C)

find_package(sombok REQUIRED)

add_executable(test_sombok test_sombok.c)
target_link_libraries(test_sombok sombok::sombok)
