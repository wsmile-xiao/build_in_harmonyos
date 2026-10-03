cmake_minimum_required(VERSION 3.15)
project(test_tasmanian CXX)

# Consumer links the packaged library through the exported CMake target.
# The package also ships the upstream Tasmanian CMake package config; both
# configs define the same target name, so either resolution path works.
find_package(Tasmanian REQUIRED)

add_executable(test_tasmanian test_tasmanian.cpp)
target_link_libraries(test_tasmanian PRIVATE Tasmanian::Tasmanian)
set_target_properties(test_tasmanian PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)
