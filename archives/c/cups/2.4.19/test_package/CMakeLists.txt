cmake_minimum_required(VERSION 3.15)
project(test_cups C)

find_package(cups CONFIG REQUIRED)

add_executable(test_cups test_cups.c)
target_link_libraries(test_cups PRIVATE cups::cups)
set_property(TARGET test_cups PROPERTY C_STANDARD 99)
