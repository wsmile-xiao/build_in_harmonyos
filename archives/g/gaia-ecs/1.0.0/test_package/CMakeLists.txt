cmake_minimum_required(VERSION 3.15)
project(test_gaia_ecs CXX)

find_package(gaia REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE gaia::gaia)

enable_testing()
add_test(NAME test_package COMMAND test_package)
