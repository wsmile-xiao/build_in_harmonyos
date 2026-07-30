cmake_minimum_required(VERSION 3.16)
project(test_sparsehash LANGUAGES CXX)

find_package(sparsehash CONFIG REQUIRED)

add_executable(test_sparsehash test.cpp)
target_compile_features(test_sparsehash PRIVATE cxx_std_11)
target_link_libraries(test_sparsehash PRIVATE sparsehash::sparsehash)
