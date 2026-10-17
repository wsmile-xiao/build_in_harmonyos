cmake_minimum_required(VERSION 3.15)
project(test_kyoto_cabinet CXX)

find_package(kyoto-cabinet REQUIRED)

add_executable(test_kyoto_cabinet test.cpp)
target_link_libraries(test_kyoto_cabinet PRIVATE kyoto-cabinet::kyoto-cabinet)

# C++11 required (KC headers use std::unordered_map etc.)
target_compile_features(test_kyoto_cabinet PRIVATE cxx_std_11)
set_target_properties(test_kyoto_cabinet PROPERTIES CXX_STANDARD 11)
