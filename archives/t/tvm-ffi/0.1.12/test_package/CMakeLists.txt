cmake_minimum_required(VERSION 3.15)
project(tvm_ffi_test_package LANGUAGES CXX)

find_package(tvm_ffi CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(test_package PRIVATE tvm_ffi::tvm_ffi)

enable_testing()
add_test(NAME test_package COMMAND test_package)
