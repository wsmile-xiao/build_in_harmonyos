cmake_minimum_required(VERSION 3.15)
project(test_odpi C)

set(CMAKE_C_STANDARD 11)

find_package(dpi REQUIRED CONFIG)

add_executable(test_odpi test.c)
target_link_libraries(test_odpi PRIVATE dpi::odpic)

enable_testing()
add_test(NAME test_odpi COMMAND test_odpi)
