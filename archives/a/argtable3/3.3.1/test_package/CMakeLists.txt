cmake_minimum_required(VERSION 3.15)
project(test_argtable3 C)

find_package(argtable3 CONFIG REQUIRED)

add_executable(test_argtable3 test_argtable3.c)
target_link_libraries(test_argtable3 PRIVATE argtable3::argtable3)
