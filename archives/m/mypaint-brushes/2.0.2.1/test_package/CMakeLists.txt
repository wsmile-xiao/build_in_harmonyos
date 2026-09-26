cmake_minimum_required(VERSION 3.15)
project(mypaint_brush_probe CXX)

add_executable(mypaint_brush_probe mypaint_brush_probe.cpp)
target_compile_features(mypaint_brush_probe PRIVATE cxx_std_11)
