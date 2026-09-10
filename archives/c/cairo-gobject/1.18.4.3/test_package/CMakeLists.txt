cmake_minimum_required(VERSION 3.16)
project(test_cairo_gobject C)

find_package(cairo-gobject REQUIRED CONFIG)

add_executable(test_cairo_gobject test_cairo_gobject.c)
target_link_libraries(test_cairo_gobject PRIVATE cairo-gobject::cairo-gobject)
