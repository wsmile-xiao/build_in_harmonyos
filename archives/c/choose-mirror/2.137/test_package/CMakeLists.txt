cmake_minimum_required(VERSION 3.15)
project(test_choose-mirror C)

add_executable(test_choose-mirror test.c)

enable_testing()
add_test(NAME test_choose-mirror COMMAND test_choose-mirror)
