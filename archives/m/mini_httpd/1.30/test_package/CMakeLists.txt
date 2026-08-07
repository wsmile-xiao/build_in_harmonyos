cmake_minimum_required(VERSION 3.15)
project(test_mini_httpd C)

add_executable(test_mini_httpd test.c)

enable_testing()
add_test(NAME test_mini_httpd COMMAND test_mini_httpd)
