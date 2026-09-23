cmake_minimum_required(VERSION 3.15)
project(test_mimetic CXX)

find_package(mimetic REQUIRED)

add_executable(test_mimetic test_mimetic.cpp)
target_link_libraries(test_mimetic PRIVATE mimetic::mimetic)
