cmake_minimum_required(VERSION 3.15)
project(test_nsnake C)

add_executable(test_nsnake test.c)

enable_testing()
add_test(NAME test_nsnake COMMAND test_nsnake)
