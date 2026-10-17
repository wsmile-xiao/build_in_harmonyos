cmake_minimum_required(VERSION 3.10)
project(test_package LANGUAGES C CXX)

find_package(workflow REQUIRED CONFIG)

add_executable(test_package test_package.cc)
target_link_libraries(test_package PRIVATE workflow::workflow pthread)
