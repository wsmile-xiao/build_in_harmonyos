cmake_minimum_required(VERSION 3.16)
project(test_google_sparsehash LANGUAGES CXX)

find_package(google-sparsehash CONFIG REQUIRED)

add_executable(test_google_sparsehash test.cpp)
target_compile_features(test_google_sparsehash PRIVATE cxx_std_11)
target_link_libraries(test_google_sparsehash PRIVATE google-sparsehash::google-sparsehash)
