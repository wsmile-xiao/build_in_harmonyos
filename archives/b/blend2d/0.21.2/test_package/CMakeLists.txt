cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(blend2d REQUIRED)

enable_testing()
add_executable(test_blend2d test_blend2d.cpp)
target_link_libraries(test_blend2d blend2d::blend2d)
add_test(NAME blend2d_test COMMAND test_blend2d)
