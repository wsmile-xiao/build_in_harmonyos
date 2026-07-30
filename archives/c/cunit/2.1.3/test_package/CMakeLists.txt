cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(cunit REQUIRED)

add_executable(test_cunit test_cunit.c)
target_link_libraries(test_cunit cunit::cunit)
