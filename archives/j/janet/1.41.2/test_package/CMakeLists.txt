cmake_minimum_required(VERSION 3.15)
project(test_janet C)

find_package(janet REQUIRED)

add_executable(test_janet test.c)
target_link_libraries(test_janet janet::janet)

enable_testing()
add_test(NAME test_janet COMMAND test_janet)