cmake_minimum_required(VERSION 3.15)
project(test_blitz CXX)

find_package(blitz REQUIRED)

add_executable(test_blitz test_blitz.cpp)
target_link_libraries(test_blitz blitz::blitz)
set_property(TARGET test_blitz PROPERTY CXX_STANDARD 11)
set_property(TARGET test_blitz PROPERTY CXX_STANDARD_REQUIRED ON)
