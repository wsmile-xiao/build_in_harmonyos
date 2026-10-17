cmake_minimum_required(VERSION 3.15)
project(test_cpp_httplib CXX)

find_package(httplib REQUIRED)

add_executable(test_cpp_httplib test.cpp)
target_link_libraries(test_cpp_httplib PRIVATE httplib::httplib)
set_target_properties(test_cpp_httplib PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
