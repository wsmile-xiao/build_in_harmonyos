cmake_minimum_required(VERSION 3.15)
project(test_string_view_lite CXX)

find_package(string-view-lite REQUIRED)

add_executable(test_string_view_lite test_string_view_lite.cpp)
target_link_libraries(test_string_view_lite PRIVATE nonstd::string-view-lite)
set_target_properties(test_string_view_lite PROPERTIES CXX_STANDARD 17)
