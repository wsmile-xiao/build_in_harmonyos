cmake_minimum_required(VERSION 3.15)
project(hopscotch_consumer C)
find_package(hopscotch CONFIG REQUIRED)
add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE hopscotch::hopscotch)

enable_testing()
add_test(NAME hopscotch_api_consumer COMMAND test_package)
