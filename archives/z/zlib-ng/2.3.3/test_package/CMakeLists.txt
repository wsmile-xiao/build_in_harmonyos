cmake_minimum_required(VERSION 3.15)
project(test_zlib-ng C)

find_package(zlib-ng REQUIRED CONFIG)

add_executable(test_zlib-ng test.c)
target_link_libraries(test_zlib-ng zlib-ng::zlib-ng)

enable_testing()
add_test(NAME test_zlib-ng COMMAND test_zlib-ng)
