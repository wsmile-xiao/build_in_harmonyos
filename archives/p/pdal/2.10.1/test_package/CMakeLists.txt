cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(PDAL REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
# CMakeDeps generates the `pdal::pdal` target from the recipe's
# cmake_file_name/cmake_target_name properties (the upstream-installed
# lib/cmake/PDAL config is removed from the package to avoid a conflict).
target_link_libraries(test_package PRIVATE pdal::pdal)
