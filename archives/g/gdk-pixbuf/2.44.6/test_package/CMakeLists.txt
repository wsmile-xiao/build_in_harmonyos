cmake_minimum_required(VERSION 3.15)
project(test_gdk_pixbuf C)

find_package(gdk-pixbuf REQUIRED CONFIG)

add_executable(test_gdk_pixbuf test.c)
target_link_libraries(test_gdk_pixbuf PRIVATE gdk-pixbuf::gdk-pixbuf)
