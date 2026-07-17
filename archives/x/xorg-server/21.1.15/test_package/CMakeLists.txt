cmake_minimum_required(VERSION 3.15)
project(test_xorg)

find_package(X11 REQUIRED)

add_executable(test_xorg test.cpp)
target_link_libraries(test_xorg X11::X11)
