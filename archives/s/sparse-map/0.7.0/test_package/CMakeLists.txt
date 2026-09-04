cmake_minimum_required(VERSION 3.15)
project(sparse_map_consumer LANGUAGES CXX)

find_package(tsl-sparse-map CONFIG REQUIRED)

add_executable(sparse_map_consumer main.cpp)
target_link_libraries(sparse_map_consumer PRIVATE tsl::sparse_map)
target_compile_features(sparse_map_consumer PRIVATE cxx_std_17)
