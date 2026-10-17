cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(GTest REQUIRED CONFIG)

add_executable(test_gtest test.cpp)
target_link_libraries(test_gtest PRIVATE GTest::gtest_main GTest::gmock)
set_property(TARGET test_gtest PROPERTY CXX_STANDARD 17)
