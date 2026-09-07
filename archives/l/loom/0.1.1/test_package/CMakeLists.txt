cmake_minimum_required(VERSION 3.15)
project(test_loom C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(loom CONFIG REQUIRED)

add_executable(test_loom test_loom.c)
target_link_libraries(test_loom PRIVATE loom::loom)

enable_testing()
add_test(NAME test_loom COMMAND test_loom)
