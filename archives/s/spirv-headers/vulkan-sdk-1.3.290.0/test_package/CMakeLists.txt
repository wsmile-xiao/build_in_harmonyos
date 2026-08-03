cmake_minimum_required(VERSION 3.15)
project(spirv_headers_test_package LANGUAGES C CXX)

find_package(SPIRV-Headers REQUIRED CONFIG)

add_executable(spirv_headers_c_test test_package.c)
target_link_libraries(
    spirv_headers_c_test
    PRIVATE
        SPIRV-Headers::SPIRV-Headers
)

add_executable(spirv_headers_cpp_test test_package.cpp)
target_link_libraries(
    spirv_headers_cpp_test
    PRIVATE
        SPIRV-Headers::SPIRV-Headers
)
target_compile_features(spirv_headers_cpp_test PRIVATE cxx_std_11)

enable_testing()
add_test(NAME spirv_headers_c_test COMMAND spirv_headers_c_test)
add_test(NAME spirv_headers_cpp_test COMMAND spirv_headers_cpp_test)
