cmake_minimum_required(VERSION 3.5)
project(debug_assert_test_package CXX)

find_package(debug_assert REQUIRED CONFIG)

add_executable(example example.cpp)
target_compile_features(example PRIVATE cxx_std_11)
target_link_libraries(example PRIVATE debug_assert::debug_assert)