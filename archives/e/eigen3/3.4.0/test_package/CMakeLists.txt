cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Eigen3 CONFIG REQUIRED)

add_executable(test_package test.cpp)
target_link_libraries(test_package Eigen3::Eigen)
target_compile_features(test_package PRIVATE cxx_std_11)