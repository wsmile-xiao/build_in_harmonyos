cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(magic_enum REQUIRED)

add_executable(test_magic_enum test_magic_enum.cpp)
target_link_libraries(test_magic_enum PRIVATE magic_enum::magic_enum)
set_property(TARGET test_magic_enum PROPERTY CXX_STANDARD 17)
set_property(TARGET test_magic_enum PROPERTY CXX_STANDARD_REQUIRED ON)
