cmake_minimum_required(VERSION 3.15)
project(test_admesh C)

find_package(admesh CONFIG REQUIRED)

add_executable(test_admesh test.c)
target_link_libraries(test_admesh PRIVATE admesh::admesh)
