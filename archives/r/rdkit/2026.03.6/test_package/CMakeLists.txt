cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(RDKit REQUIRED)

add_executable(test_package src/main.cpp)
target_link_libraries(test_package RDKit::rdkit)
target_compile_features(test_package PRIVATE cxx_std_17)
