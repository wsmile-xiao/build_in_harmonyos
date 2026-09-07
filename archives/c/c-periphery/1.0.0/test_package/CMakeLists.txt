cmake_minimum_required(VERSION 3.15)
project(test_periphery C)

find_package(c-periphery REQUIRED)

add_executable(test_periphery test_periphery.c)
target_link_libraries(test_periphery PRIVATE c-periphery::c-periphery)

enable_testing()
add_test(NAME test_periphery COMMAND test_periphery)
