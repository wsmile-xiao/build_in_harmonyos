cmake_minimum_required(VERSION 3.15)
project(test_span_lite CXX)

find_package(span-lite REQUIRED)

add_executable(test_span_lite test_span_lite.cpp)
target_link_libraries(test_span_lite PRIVATE nonstd::span-lite)
set_target_properties(test_span_lite PROPERTIES CXX_STANDARD 17)
