cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(namedtype REQUIRED)

add_executable(test_namedtype test.cpp)
target_link_libraries(test_namedtype PRIVATE namedtype::namedtype)
set_property(TARGET test_namedtype PROPERTY CXX_STANDARD 17)
set_property(TARGET test_namedtype PROPERTY CXX_STANDARD_REQUIRED ON)
