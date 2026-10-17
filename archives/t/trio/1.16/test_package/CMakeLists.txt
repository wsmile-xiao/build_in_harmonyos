cmake_minimum_required(VERSION 3.16)
project(test_package C)

find_package(trio REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE trio::trio)