cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(dlpack REQUIRED)

add_executable(test_dlpack test.cpp)
target_link_libraries(test_dlpack PRIVATE dlpack::dlpack)
set_property(TARGET test_dlpack PROPERTY CXX_STANDARD 11)