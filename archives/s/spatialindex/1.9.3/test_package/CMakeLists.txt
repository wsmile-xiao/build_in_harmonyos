cmake_minimum_required(VERSION 3.10)
project(test_sidx CXX)

find_package(spatialindex REQUIRED)

add_executable(test_sidx test_sidx.cpp)
target_link_libraries(test_sidx PRIVATE spatialindex::spatialindex)
