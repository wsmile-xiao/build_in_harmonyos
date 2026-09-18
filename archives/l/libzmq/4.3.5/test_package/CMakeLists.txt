cmake_minimum_required(VERSION 3.5)
project(test_package LANGUAGES C CXX)

find_package(ZeroMQ REQUIRED)

add_executable(test_package test_libzmq.c)
target_link_libraries(test_package PRIVATE libzmq)
