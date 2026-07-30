cmake_minimum_required(VERSION 3.15)
project(test_ggml CXX)

find_package(ggml CONFIG REQUIRED)

add_executable(test_ggml test_ggml.cpp)
target_compile_features(test_ggml PRIVATE cxx_std_17)
target_link_libraries(test_ggml PRIVATE ggml::ggml)
