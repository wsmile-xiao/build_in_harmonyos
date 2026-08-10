cmake_minimum_required(VERSION 3.15)
project(test_ndisc6 C)

add_executable(test_ndisc6 test.c)

enable_testing()
add_test(NAME test_ndisc6 COMMAND test_ndisc6)
