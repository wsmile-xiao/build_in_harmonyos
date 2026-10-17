cmake_minimum_required(VERSION 3.15)
project(test_words_es LANGUAGES CXX)

add_executable(test_words_es test_words_es.cpp)
target_compile_features(test_words_es PRIVATE cxx_std_17)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(test_words_es PRIVATE -Wall -Wextra -Wpedantic)
endif()
