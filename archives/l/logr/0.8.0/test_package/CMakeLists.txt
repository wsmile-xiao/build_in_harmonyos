cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(logr CONFIG REQUIRED)
find_package(fmt CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE logr::logr_base fmt::fmt)
target_compile_features(test_package PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_package COMMAND test_package)