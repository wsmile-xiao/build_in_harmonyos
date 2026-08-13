cmake_minimum_required(VERSION 3.15)
project(p11_kit_test_package C)

find_package(p11-kit CONFIG REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE p11-kit::p11-kit)
