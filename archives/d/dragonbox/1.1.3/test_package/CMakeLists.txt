cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(dragonbox REQUIRED)

add_executable(test_dragonbox test.cpp)
target_link_libraries(test_dragonbox PRIVATE dragonbox::dragonbox)
set_property(TARGET test_dragonbox PROPERTY CXX_STANDARD 17)
set_property(TARGET test_dragonbox PROPERTY CXX_STANDARD_REQUIRED ON)