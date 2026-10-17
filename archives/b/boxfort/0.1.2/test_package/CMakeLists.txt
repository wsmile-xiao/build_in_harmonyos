cmake_minimum_required(VERSION 3.15)
project(test_boxfort C)

find_package(boxfort CONFIG REQUIRED)

add_executable(test_package test_boxfort.c)
target_link_libraries(test_package PRIVATE boxfort::boxfort)

enable_testing()
add_test(NAME boxfort_consumer COMMAND test_package)
