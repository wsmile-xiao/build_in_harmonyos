cmake_minimum_required(VERSION 3.15)
project(test_lcms C)

find_package(lcms2 REQUIRED CONFIG)

add_executable(test_lcms test.c)
target_link_libraries(test_lcms PRIVATE lcms2::lcms2)
