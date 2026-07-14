cmake_minimum_required(VERSION 3.15)
project(test_cpputest CXX)

find_package(CppUTest REQUIRED)

add_executable(test_cpputest test_cpputest.cpp)
target_link_libraries(test_cpputest PRIVATE CppUTest::CppUTest)
