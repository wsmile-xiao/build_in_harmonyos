cmake_minimum_required(VERSION 3.15)
project(libslax_test_package C)

find_package(libslax CONFIG REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE libslax::libslax)
