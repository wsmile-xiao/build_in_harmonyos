cmake_minimum_required(VERSION 3.15)
project(test_blake2 C)

find_package(blake2 REQUIRED)

add_executable(test_blake2 test.c)
target_link_libraries(test_blake2 PRIVATE blake2::blake2)

enable_testing()
add_test(NAME test_blake2 COMMAND test_blake2)