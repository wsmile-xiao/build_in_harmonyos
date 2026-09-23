cmake_minimum_required(VERSION 3.15)
project(test_colibri_core LANGUAGES CXX)

find_package(colibri-core CONFIG REQUIRED)

add_executable(test_colibri_core test_colibri_core.cpp)
target_compile_features(test_colibri_core PRIVATE cxx_std_11)
target_link_libraries(test_colibri_core PRIVATE colibri-core::colibri-core)
