cmake_minimum_required(VERSION 3.15)
project(test_hunspell_ca LANGUAGES CXX)

add_executable(test_hunspell_ca test_hunspell_ca.cpp)
target_compile_features(test_hunspell_ca PRIVATE cxx_std_11)
