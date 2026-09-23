cmake_minimum_required(VERSION 3.15)
project(test_liborigin LANGUAGES CXX)

find_package(liborigin REQUIRED CONFIG)

add_executable(test_liborigin test_liborigin.cpp)
target_compile_features(test_liborigin PRIVATE cxx_std_17)
target_link_libraries(test_liborigin PRIVATE liborigin::liborigin)
