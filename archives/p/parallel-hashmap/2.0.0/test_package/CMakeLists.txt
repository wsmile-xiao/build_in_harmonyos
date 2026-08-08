cmake_minimum_required(VERSION 3.13)
project(phmap_test CXX)

find_package(phmap REQUIRED)

add_executable(phmap_test test_package.cpp)
target_link_libraries(phmap_test PRIVATE phmap::phmap)
target_compile_features(phmap_test PRIVATE cxx_std_17)
