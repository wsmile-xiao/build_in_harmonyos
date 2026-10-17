cmake_minimum_required(VERSION 3.15)
project(test_mpg123 C)

find_package(mpg123 REQUIRED)

add_executable(test_mpg123 test.c)
target_link_libraries(test_mpg123 mpg123::mpg123)

enable_testing()
add_test(NAME mpg123_api_test COMMAND test_mpg123)
