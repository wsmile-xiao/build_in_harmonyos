cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(fmt CONFIG REQUIRED)

add_executable(test_probe test.cpp)
target_link_libraries(test_probe PRIVATE fmt::fmt)
target_compile_features(test_probe PRIVATE cxx_std_17)