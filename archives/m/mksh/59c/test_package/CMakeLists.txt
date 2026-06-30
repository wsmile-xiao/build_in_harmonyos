cmake_minimum_required(VERSION 3.15)
project(test_mksh C)

# mksh is a binary tool, not a library — no find_package needed
add_executable(test_mksh test.c)

enable_testing()
add_test(NAME test_mksh COMMAND test_mksh)
