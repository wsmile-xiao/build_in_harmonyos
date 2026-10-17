cmake_minimum_required(VERSION 3.16)
project(test_package C)

find_package(ls-hpack REQUIRED)

add_executable(test_package test_package.c)
# Target name from recipe's cmake_target_name = ls-hpack::ls-hpack
target_link_libraries(test_package PRIVATE ls-hpack::ls-hpack)

enable_testing()
add_test(NAME test_package COMMAND test_package)
