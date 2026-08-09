cmake_minimum_required(VERSION 3.15)
project(acf_skins_test LANGUAGES CXX)

add_executable(skin_probe skin_probe.cpp)
target_compile_features(skin_probe PRIVATE cxx_std_11)
