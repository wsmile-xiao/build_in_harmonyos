cmake_minimum_required(VERSION 3.15)
project(test_burst LANGUAGES CXX)

find_package(Burst CONFIG REQUIRED)

add_executable(test_burst test.cpp)
target_link_libraries(test_burst PRIVATE Burst::burst)
target_compile_features(test_burst PRIVATE cxx_std_14)
