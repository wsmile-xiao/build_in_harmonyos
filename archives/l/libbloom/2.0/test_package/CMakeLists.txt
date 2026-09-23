cmake_minimum_required(VERSION 3.15)
project(test_bloom C)

find_package(libbloom REQUIRED)

add_executable(test_bloom test_bloom.c)
target_link_libraries(test_bloom libbloom::libbloom)

enable_testing()
add_test(NAME test_bloom COMMAND test_bloom)
