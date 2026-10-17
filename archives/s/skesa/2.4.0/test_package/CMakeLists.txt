cmake_minimum_required(VERSION 3.15)
project(test_skesa CXX)

add_executable(test_skesa test_skesa.cpp)
target_compile_features(test_skesa PRIVATE cxx_std_11)
