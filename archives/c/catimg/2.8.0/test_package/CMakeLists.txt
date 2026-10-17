cmake_minimum_required(VERSION 3.15)
project(test_catimg C)

add_executable(test_catimg test.c)

enable_testing()
add_test(NAME test_catimg COMMAND test_catimg)
