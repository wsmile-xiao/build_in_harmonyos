cmake_minimum_required(VERSION 3.15)

project(ruckig_test_package LANGUAGES CXX)

find_package(ruckig CONFIG REQUIRED)

add_executable(ruckig_test test_main.cpp)
target_compile_features(ruckig_test PRIVATE cxx_std_20)
target_link_libraries(ruckig_test PRIVATE ruckig::ruckig)
