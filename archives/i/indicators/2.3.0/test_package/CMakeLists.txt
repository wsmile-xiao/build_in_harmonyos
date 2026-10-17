cmake_minimum_required(VERSION 3.15)
project(test_indicators CXX)

find_package(indicators REQUIRED)

add_executable(test_indicators test_indicators.cpp)
target_link_libraries(test_indicators PRIVATE indicators::indicators)
set_target_properties(test_indicators PROPERTIES CXX_STANDARD 17)