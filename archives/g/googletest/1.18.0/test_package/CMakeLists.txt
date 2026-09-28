cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(GTest REQUIRED)

add_executable(test_googletest test_googletest.cpp)
target_link_libraries(
    test_googletest
    PRIVATE
        GTest::gmock
        GTest::gtest_main
)
set_property(TARGET test_googletest PROPERTY CXX_STANDARD 17)
set_property(TARGET test_googletest PROPERTY CXX_STANDARD_REQUIRED ON)
