cmake_minimum_required(VERSION 3.15)
project(libzeitgeist_test_package C)

find_package(libzeitgeist REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package libzeitgeist::libzeitgeist)
