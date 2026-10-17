cmake_minimum_required(VERSION 3.15)
project(test_words_de LANGUAGES CXX)

add_executable(test_words_de test_words_de.cpp)
target_compile_features(test_words_de PRIVATE cxx_std_11)
