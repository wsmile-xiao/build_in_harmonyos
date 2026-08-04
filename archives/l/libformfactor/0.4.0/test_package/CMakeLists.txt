cmake_minimum_required(VERSION 3.20)
project(test_libformfactor LANGUAGES CXX)

find_package(formfactor CONFIG REQUIRED)

add_executable(test_libformfactor test.cpp)
target_compile_features(test_libformfactor PRIVATE cxx_std_20)
target_link_libraries(test_libformfactor PRIVATE formfactor::formfactor)
