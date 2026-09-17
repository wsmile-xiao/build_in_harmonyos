cmake_minimum_required(VERSION 3.15)
project(test_libbde C)

find_package(libbde REQUIRED)

add_executable(test_libbde test_libbde.c)
target_link_libraries(test_libbde libbde::libbde)

enable_testing()
add_test(NAME test_libbde COMMAND test_libbde)
