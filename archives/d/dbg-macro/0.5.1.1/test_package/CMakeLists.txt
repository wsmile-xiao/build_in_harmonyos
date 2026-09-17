cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(dbg_macro REQUIRED)

add_executable(test_dbg_macro test.cpp)
target_link_libraries(test_dbg_macro PRIVATE dbg_macro::dbg_macro)
set_property(TARGET test_dbg_macro PROPERTY CXX_STANDARD 11)
set_property(TARGET test_dbg_macro PROPERTY CXX_STANDARD_REQUIRED ON)
