cmake_minimum_required(VERSION 3.15)
project(test_chrootuid C)

add_executable(test_chrootuid test.c)

enable_testing()
add_test(NAME test_chrootuid COMMAND test_chrootuid)
