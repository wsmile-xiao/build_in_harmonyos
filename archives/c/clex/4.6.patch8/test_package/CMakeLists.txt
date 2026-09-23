cmake_minimum_required(VERSION 3.15)
project(test_clex C)

add_executable(test_clex test.c)

enable_testing()
add_test(NAME test_clex COMMAND test_clex)
