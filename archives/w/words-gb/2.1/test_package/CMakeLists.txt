cmake_minimum_required(VERSION 3.15)
project(test_words_gb LANGUAGES CXX)

add_executable(test_words_gb test_words_gb.cpp)
target_compile_features(test_words_gb PRIVATE cxx_std_11)
