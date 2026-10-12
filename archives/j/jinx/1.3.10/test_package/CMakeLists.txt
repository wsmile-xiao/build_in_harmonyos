cmake_minimum_required(VERSION 3.16)
project(jinx_test_package LANGUAGES CXX)

find_package(Jinx CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Jinx::Jinx)
target_compile_features(test_package PRIVATE cxx_std_17)

add_executable(harmonyos_test harmonyos_test.cpp)
target_link_libraries(harmonyos_test PRIVATE Jinx::Jinx)
target_compile_features(harmonyos_test PRIVATE cxx_std_17)
