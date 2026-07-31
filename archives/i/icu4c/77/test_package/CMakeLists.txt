cmake_minimum_required(VERSION 3.15)
project(test_icu4c LANGUAGES CXX)

find_package(icu4c CONFIG REQUIRED)

add_executable(test_icu4c test_icu4c.cpp)
target_compile_features(test_icu4c PRIVATE cxx_std_17)
target_link_libraries(test_icu4c PRIVATE icu4c::icu4c)
