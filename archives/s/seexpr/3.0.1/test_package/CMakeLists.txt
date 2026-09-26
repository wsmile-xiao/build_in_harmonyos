cmake_minimum_required(VERSION 3.15)
project(test_seexpr CXX)

find_package(seexpr CONFIG REQUIRED)

add_executable(test_seexpr test.cpp)
target_link_libraries(test_seexpr seexpr::seexpr)
