cmake_minimum_required(VERSION 3.15)
project(test_libcaption C)

find_package(caption REQUIRED CONFIG)

add_executable(test_libcaption test.c)
target_link_libraries(test_libcaption PRIVATE caption::caption)
