cmake_minimum_required(VERSION 3.15)
project(test_ptl LANGUAGES CXX)

find_package(PTL REQUIRED CONFIG)

add_executable(test_ptl test_ptl.cpp)
target_link_libraries(test_ptl PRIVATE PTL::ptl)
target_compile_features(test_ptl PRIVATE cxx_std_17)
