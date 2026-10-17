cmake_minimum_required(VERSION 3.15)
project(cling_test_package LANGUAGES CXX)

find_package(cling CONFIG REQUIRED)

add_executable(cling_embedding embedding.cpp)
target_compile_features(cling_embedding PRIVATE cxx_std_17)
target_link_libraries(cling_embedding PRIVATE cling::cling)
