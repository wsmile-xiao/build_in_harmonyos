cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

include(CTest)

find_package(ctre REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE ctre::ctre)
target_compile_features(test_package PRIVATE cxx_std_17)

if(BUILD_TESTING)
  add_test(NAME test_package COMMAND test_package)
endif()
