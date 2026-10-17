cmake_minimum_required(VERSION 3.15)
project(omath_test_package LANGUAGES CXX)

find_package(omath REQUIRED CONFIG)

add_executable(test_omath test_omath.cpp)
target_link_libraries(test_omath PRIVATE omath::omath)
set_target_properties(test_omath PROPERTIES CXX_STANDARD 23 CXX_STANDARD_REQUIRED ON)
