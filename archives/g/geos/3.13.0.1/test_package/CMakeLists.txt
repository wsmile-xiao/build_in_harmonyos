cmake_minimum_required(VERSION 3.15)
project(test_geos CXX)

find_package(GEOS REQUIRED CONFIG)

add_executable(test_geos test_geos.cpp)
target_link_libraries(test_geos PRIVATE GEOS::geos_c)
