cmake_minimum_required(VERSION 3.16)
project(test_triangle C)

set(CMAKE_C_STANDARD 17)

enable_testing()

find_package(triangle REQUIRED)

add_executable(test_triangle src/test_triangle.c)
target_link_libraries(test_triangle triangle::triangle)

add_test(NAME triangle_consumer COMMAND test_triangle)
