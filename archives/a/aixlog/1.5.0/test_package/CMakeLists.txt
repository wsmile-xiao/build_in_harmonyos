cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(aixlog REQUIRED)

add_executable(test_aixlog test.cpp)
target_link_libraries(test_aixlog PRIVATE aixlog::aixlog)
set_property(TARGET test_aixlog PROPERTY CXX_STANDARD 11)
set_property(TARGET test_aixlog PROPERTY CXX_STANDARD_REQUIRED ON)
