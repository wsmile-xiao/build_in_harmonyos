cmake_minimum_required(VERSION 3.16)
project(test_mlddc C)

add_executable(test_mlddc test.c)
enable_testing()
add_test(NAME test_mlddc COMMAND test_mlddc)
