cmake_minimum_required(VERSION 3.15)
project(plusaes_test_package CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Consumer view: only the packaged header tree is visible here.
find_package(plusaes REQUIRED CONFIG)

add_executable(test_package example.cpp)
target_link_libraries(test_package plusaes::plusaes)

# Deterministic location so test_package/conanfile.py can self.run() the
# binary directly (L0d requires a real self.run(), not cmake.test()).
set_target_properties(test_package PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
