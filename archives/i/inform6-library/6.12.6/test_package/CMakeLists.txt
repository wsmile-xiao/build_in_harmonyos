cmake_minimum_required(VERSION 3.15)
project(inform6lib_test LANGUAGES CXX)
add_executable(inform6lib_probe inform6lib_probe.cpp)
target_compile_features(inform6lib_probe PRIVATE cxx_std_11)
