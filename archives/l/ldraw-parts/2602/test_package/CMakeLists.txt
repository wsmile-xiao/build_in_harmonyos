cmake_minimum_required(VERSION 3.15)
project(ldraw_parts_test LANGUAGES CXX)
add_executable(ldraw_parts_probe ldraw_parts_probe.cpp)
target_compile_features(ldraw_parts_probe PRIVATE cxx_std_11)
