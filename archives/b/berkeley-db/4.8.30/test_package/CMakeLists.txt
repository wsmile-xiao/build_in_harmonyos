cmake_minimum_required(VERSION 3.15)
project(test_package C)

add_executable(test_package test.c)
find_package(berkeley-db CONFIG REQUIRED)
target_link_libraries(test_package PRIVATE berkeley-db::berkeley-db)
