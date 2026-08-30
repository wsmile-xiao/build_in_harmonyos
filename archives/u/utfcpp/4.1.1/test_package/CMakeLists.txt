cmake_minimum_required(VERSION 3.15)
project(test_utfcpp CXX)

find_package(utf8cpp REQUIRED)

add_executable(test_utfcpp test.cpp)
target_link_libraries(test_utfcpp PRIVATE utf8cpp::utf8cpp)
set_target_properties(test_utfcpp PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)
