cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(dxflib REQUIRED)

add_executable(test_dxflib test.cpp)
target_link_libraries(test_dxflib PRIVATE dxflib::dxflib)
set_property(TARGET test_dxflib PROPERTY CXX_STANDARD 11)