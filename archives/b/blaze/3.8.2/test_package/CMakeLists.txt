cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)
enable_testing()

find_package(Blaze CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Blaze::Blaze)
target_compile_features(test_package PRIVATE cxx_std_14)
add_test(NAME blaze_test_package COMMAND test_package)
