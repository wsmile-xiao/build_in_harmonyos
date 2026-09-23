cmake_minimum_required(VERSION 3.15)
project(test_scrypt C)

add_executable(test_scrypt test.c)
target_link_libraries(test_scrypt)

enable_testing()
add_test(NAME test_scrypt COMMAND test_scrypt)
