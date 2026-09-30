cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(meojson REQUIRED)

add_executable(test_meojson test_meojson.cpp)
target_link_libraries(test_meojson PRIVATE meojson::meojson)
set_property(TARGET test_meojson PROPERTY CXX_STANDARD 17)
set_property(TARGET test_meojson PROPERTY CXX_STANDARD_REQUIRED ON)
