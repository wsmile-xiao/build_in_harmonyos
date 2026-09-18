cmake_minimum_required(VERSION 3.8)
project(test_package CXX)

find_package(jinja2cpp REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE jinja2cpp::jinja2cpp)
