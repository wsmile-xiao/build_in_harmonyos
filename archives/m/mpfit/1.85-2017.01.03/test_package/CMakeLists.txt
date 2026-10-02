cmake_minimum_required(VERSION 3.15)
project(test_mpfit C)

find_package(mpfit CONFIG REQUIRED)

add_executable(test_mpfit test.c)
target_link_libraries(test_mpfit mpfit::mpfit)
