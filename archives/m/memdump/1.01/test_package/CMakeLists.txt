cmake_minimum_required(VERSION 3.15)
project(test_memdump C)

add_executable(test_memdump test.c)

enable_testing()
add_test(NAME test_memdump COMMAND test_memdump)
