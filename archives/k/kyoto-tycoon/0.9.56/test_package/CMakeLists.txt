cmake_minimum_required(VERSION 3.15)
project(test_kyoto_tycoon CXX)

find_package(kyoto-tycoon REQUIRED)
# test.cpp also uses kyoto-cabinet headers directly (kccommon.h,
# kc::BasicDB, kyotocabinet::File), so find and link it explicitly;
# the main recipe additionally propagates it via cpp_info.requires.
find_package(kyoto-cabinet REQUIRED)

add_executable(test_kyoto_tycoon test.cpp)
target_link_libraries(test_kyoto_tycoon PRIVATE kyoto-tycoon::kyoto-tycoon kyoto-cabinet::kyoto-cabinet)

# C++11 required (KT headers use std::map/vector etc.)
target_compile_features(test_kyoto_tycoon PRIVATE cxx_std_11)
set_target_properties(test_kyoto_tycoon PROPERTIES CXX_STANDARD 11)
