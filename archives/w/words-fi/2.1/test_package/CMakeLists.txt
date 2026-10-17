cmake_minimum_required(VERSION 3.15)
project(test_words_fi LANGUAGES CXX)

add_executable(test_words_fi test_words_fi.cpp)
target_compile_features(test_words_fi PRIVATE cxx_std_17)
target_compile_options(test_words_fi PRIVATE -Wall -Wextra -Wpedantic)
