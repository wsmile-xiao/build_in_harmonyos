cmake_minimum_required(VERSION 3.15)
project(test_libmesode C)

find_package(libmesode REQUIRED)

add_executable(test_libmesode test.c)
target_link_libraries(test_libmesode libmesode::libmesode)

enable_testing()
add_test(NAME test_libmesode COMMAND test_libmesode)
