cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

# PoseLib public headers require C++17 (upstream target_compile_features
# cxx_std_17 PUBLIC)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PoseLib REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE PoseLib::PoseLib)

enable_testing()
add_test(NAME poselib_consumer_test COMMAND test_package)
