cmake_minimum_required(VERSION 3.15)
project(test_daw_utf_range CXX)

find_package(daw-utf-range REQUIRED)
find_package(daw-header-libraries REQUIRED)

add_executable(test_daw_utf_range test_daw_utf_range.cpp)
target_link_libraries(test_daw_utf_range PRIVATE daw::daw-utf-range)
set_target_properties(test_daw_utf_range PROPERTIES CXX_STANDARD 17)
