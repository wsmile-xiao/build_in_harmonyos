cmake_minimum_required(VERSION 3.15)
project(spirv_headers_test_package LANGUAGES CXX)

find_package(SPIRV-Headers REQUIRED CONFIG)

add_executable(spirv_headers_test test_package.cpp)
target_link_libraries(
    spirv_headers_test
    PRIVATE
        SPIRV-Headers::SPIRV-Headers
)
target_compile_features(spirv_headers_test PRIVATE cxx_std_11)
