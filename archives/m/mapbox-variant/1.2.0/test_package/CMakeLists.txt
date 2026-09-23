cmake_minimum_required(VERSION 3.15)
project(mapbox_variant_consumer LANGUAGES CXX)

find_package(mapbox-variant CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_11)
target_link_libraries(test_package PRIVATE mapbox::variant)
set_target_properties(test_package PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
