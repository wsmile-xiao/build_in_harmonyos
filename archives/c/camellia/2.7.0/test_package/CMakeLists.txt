cmake_minimum_required(VERSION 3.15)
project(camellia_test C)

find_package(camellia CONFIG REQUIRED)

add_executable(camellia_test test.c)
target_link_libraries(camellia_test PRIVATE camellia::camellia)
