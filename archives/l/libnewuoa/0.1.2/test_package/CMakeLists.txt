cmake_minimum_required(VERSION 3.15)
project(test_newuoa C)

find_package(newuoa REQUIRED CONFIG)

add_executable(test_newuoa test_newuoa.c)
target_link_libraries(test_newuoa newuoa::newuoa)
