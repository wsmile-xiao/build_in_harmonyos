cmake_minimum_required(VERSION 3.15)
project(test_valijson CXX)

find_package(valijson REQUIRED)

add_executable(test_valijson test_valijson.cpp)
target_link_libraries(test_valijson PRIVATE valijson::valijson)
