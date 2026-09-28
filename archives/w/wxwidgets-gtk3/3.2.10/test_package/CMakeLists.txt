cmake_minimum_required(VERSION 3.15)
project(test_wxgtk3 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(wxwidgets-gtk3 CONFIG REQUIRED)

add_executable(test_wxgtk3 test_wxgtk3.cpp)
target_link_libraries(test_wxgtk3 PRIVATE wxwidgets-gtk3::wxwidgets-gtk3)
