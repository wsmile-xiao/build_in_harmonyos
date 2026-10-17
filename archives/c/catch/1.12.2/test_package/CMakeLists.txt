cmake_minimum_required(VERSION 3.15)
project(test_catch CXX)

find_package(Catch REQUIRED)

add_executable(test_catch test_catch.cpp)
target_link_libraries(test_catch PRIVATE Catch::Catch)
