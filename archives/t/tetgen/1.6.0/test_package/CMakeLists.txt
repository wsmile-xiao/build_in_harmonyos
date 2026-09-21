cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(tetgen CONFIG REQUIRED)

add_executable(test_tetgen test_tetgen.cpp)
target_link_libraries(test_tetgen PRIVATE tetgen::tetgen)
target_compile_features(test_tetgen PRIVATE cxx_std_11)
