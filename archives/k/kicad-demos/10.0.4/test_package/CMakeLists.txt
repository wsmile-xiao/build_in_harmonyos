cmake_minimum_required(VERSION 3.15)
project(kicad_demos_test LANGUAGES CXX)
add_executable(kicad_demo_probe kicad_demo_probe.cpp)
target_compile_features(kicad_demo_probe PRIVATE cxx_std_11)
