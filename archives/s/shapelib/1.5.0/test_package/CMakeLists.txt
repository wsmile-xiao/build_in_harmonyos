cmake_minimum_required(VERSION 3.15)
project(test_shapelib C)

find_package(shapelib REQUIRED)

add_executable(test_shapelib test.c)
target_link_libraries(test_shapelib PRIVATE shp::shp)
