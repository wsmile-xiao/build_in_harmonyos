cmake_minimum_required(VERSION 3.15)
project(test_dwgsim C)

add_executable(test_dwgsim test_dwgsim.c)

enable_testing()
add_test(NAME test_dwgsim COMMAND test_dwgsim)
