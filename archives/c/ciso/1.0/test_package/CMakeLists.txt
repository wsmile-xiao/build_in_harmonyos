cmake_minimum_required(VERSION 3.15)
project(test_ciso C)

add_executable(test_ciso test_ciso.c)
enable_testing()
add_test(NAME test_ciso COMMAND test_ciso)
