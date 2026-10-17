cmake_minimum_required(VERSION 3.15)
project(test_daw_header_libraries CXX)

find_package(daw-header-libraries REQUIRED)

add_executable(test_daw_header_libraries test_daw_header_libraries.cpp)
target_link_libraries(test_daw_header_libraries PRIVATE daw::daw-header-libraries)
set_target_properties(test_daw_header_libraries PROPERTIES CXX_STANDARD 17)