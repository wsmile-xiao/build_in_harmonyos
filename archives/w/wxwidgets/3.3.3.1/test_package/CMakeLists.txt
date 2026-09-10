cmake_minimum_required(VERSION 3.15)
project(test_wxwidgets LANGUAGES CXX)

find_package(wxWidgets REQUIRED CONFIG)

add_executable(test_wxwidgets test.cpp)
target_link_libraries(test_wxwidgets PRIVATE wxWidgets::wxWidgets)
