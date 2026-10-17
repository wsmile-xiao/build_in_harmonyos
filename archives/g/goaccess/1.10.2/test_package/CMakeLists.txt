cmake_minimum_required(VERSION 3.15)
project(test_goaccess C)

add_executable(test_goaccess test.goaccess.c)

enable_testing()
add_test(NAME goaccess_smoke COMMAND test_goaccess)
