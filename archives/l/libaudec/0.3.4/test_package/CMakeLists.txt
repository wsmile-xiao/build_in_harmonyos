cmake_minimum_required(VERSION 3.15)
project(test_audec C)

find_package(libaudec CONFIG REQUIRED)

add_executable(test_package test_audec.c)
target_link_libraries(test_package PRIVATE libaudec::libaudec)
target_compile_options(test_package PRIVATE -std=gnu11 -Wall)
