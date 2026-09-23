cmake_minimum_required(VERSION 3.15)
project(libytnef_test_package LANGUAGES C)

find_package(libytnef CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libytnef::libytnef)
