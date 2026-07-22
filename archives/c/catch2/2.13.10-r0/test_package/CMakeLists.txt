cmake_minimum_required(VERSION 3.15)
project(test_catch2 CXX)

find_package(Catch2 REQUIRED)

add_executable(test_catch2 test_catch2.cpp)
target_link_libraries(test_catch2 PRIVATE Catch2::Catch2)

