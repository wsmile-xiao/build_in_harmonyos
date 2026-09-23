cmake_minimum_required(VERSION 3.15)
project(test_utfcpp20 CXX)

find_package(utfcpp20 REQUIRED)

add_executable(test_utfcpp20 test_utfcpp20.cpp)
target_link_libraries(test_utfcpp20 PRIVATE utfcpp20::utfcpp20)
set_target_properties(test_utfcpp20 PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)
