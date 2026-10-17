cmake_minimum_required(VERSION 3.15)
project(test_wxwidgets CXX)

find_package(wxwidgets REQUIRED)

add_executable(test_wxwidgets test.cpp)
target_link_libraries(test_wxwidgets wxwidgets::wxwidgets)
