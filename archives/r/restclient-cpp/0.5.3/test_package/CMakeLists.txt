cmake_minimum_required(VERSION 3.15)
project(restclient_cpp_test_package LANGUAGES CXX)

find_package(restclient-cpp CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE restclient-cpp::restclient-cpp)
target_compile_features(test_package PRIVATE cxx_std_11)
