cmake_minimum_required(VERSION 3.15)
project(test_sole CXX)

find_package(sole CONFIG REQUIRED)

add_executable(test_sole test.cpp)
target_link_libraries(test_sole PRIVATE sole::sole)
set_target_properties(test_sole PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
