cmake_minimum_required(VERSION 3.18)
project(test_package_cpp_taskflow LANGUAGES CXX)

find_package(Taskflow CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Taskflow::Taskflow)
target_compile_features(test_package PRIVATE cxx_std_17)

include(CTest)
add_test(NAME test_package COMMAND test_package)