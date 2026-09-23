cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libpillowfight REQUIRED)

add_executable(test_package test_consumer.c)
target_link_libraries(test_package libpillowfight::libpillowfight)
