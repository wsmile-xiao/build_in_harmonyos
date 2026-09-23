cmake_minimum_required(VERSION 3.15)
project(test_btparse C)

find_package(btparse REQUIRED)

add_executable(test_btparse_api test_btparse_api.c)
target_link_libraries(test_btparse_api btparse::btparse)

enable_testing()
add_test(NAME test_btparse_api COMMAND test_btparse_api)
