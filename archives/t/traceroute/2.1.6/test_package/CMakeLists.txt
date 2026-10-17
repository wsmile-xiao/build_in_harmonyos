cmake_minimum_required(VERSION 3.15)
project(test_traceroute C)

add_executable(test_traceroute test.c)

enable_testing()
add_test(NAME test_traceroute COMMAND test_traceroute)
