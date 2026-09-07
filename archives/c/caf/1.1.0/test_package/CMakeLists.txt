cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(CAF REQUIRED CONFIG)

add_executable(test_caf test_package.cpp)
target_link_libraries(test_caf PRIVATE CAF::core)
target_compile_features(test_caf PRIVATE cxx_std_17)