cmake_minimum_required(VERSION 3.15)
project(test_libkqueue C)

find_package(libkqueue REQUIRED CONFIG)

add_executable(test_libkqueue test_libkqueue.c)
target_link_libraries(test_libkqueue PRIVATE libkqueue::libkqueue)
