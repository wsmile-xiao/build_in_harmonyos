cmake_minimum_required(VERSION 3.15)
project(test_bird2 C)

# bird2 is an application (daemon), not a library — no link target needed
add_executable(test_bird2 test.c)

enable_testing()
add_test(NAME test_bird2 COMMAND test_bird2)
