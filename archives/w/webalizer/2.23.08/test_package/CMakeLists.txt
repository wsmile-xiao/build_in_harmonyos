cmake_minimum_required(VERSION 3.15)
project(test_webalizer C)

enable_testing()
add_executable(test_webalizer test.c)
add_test(NAME test_webalizer COMMAND test_webalizer)
