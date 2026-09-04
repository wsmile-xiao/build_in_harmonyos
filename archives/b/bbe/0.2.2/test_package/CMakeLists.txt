cmake_minimum_required(VERSION 3.15)
project(test_bbe C)

add_executable(test_bbe test.c)
enable_testing()
add_test(NAME test_bbe COMMAND test_bbe)
