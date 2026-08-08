cmake_minimum_required(VERSION 3.15)
project(adobe_source_han_serif_jp_test LANGUAGES CXX)
add_executable(font_probe font_probe.cpp)
target_compile_features(font_probe PRIVATE cxx_std_11)
