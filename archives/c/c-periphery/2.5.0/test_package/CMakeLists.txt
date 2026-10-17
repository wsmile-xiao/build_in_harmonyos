cmake_minimum_required(VERSION 3.15)
project(test_c-periphery C)

find_package(c-periphery REQUIRED)

add_executable(test_periphery test_periphery.c)
target_link_libraries(test_periphery c-periphery::c-periphery)
