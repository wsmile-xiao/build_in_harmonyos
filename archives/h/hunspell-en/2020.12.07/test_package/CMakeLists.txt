cmake_minimum_required(VERSION 3.15)
project(test_hunspell_en LANGUAGES CXX)

add_executable(test_hunspell_en test_hunspell_en.cpp)
target_compile_features(test_hunspell_en PRIVATE cxx_std_11)
