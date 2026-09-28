cmake_minimum_required(VERSION 3.15)
project(inform_mode_test LANGUAGES CXX)
add_executable(inform_mode_probe inform_mode_probe.cpp)
target_compile_features(inform_mode_probe PRIVATE cxx_std_11)
